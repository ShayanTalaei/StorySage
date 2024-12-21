import asyncio
import uuid
from datetime import datetime
from typing import Dict, List
import signal
import contextlib

from dotenv import load_dotenv

from interview_session.session_models import Message, Participant
from agents.interviewer.interviewer import Interviewer
from agents.memory_manager.memory_manager import MemoryManager
from agents.user.user_agent import UserAgent
from session_note.session_note import SessionNote
from utils.logger import SessionLogger, setup_logger
from user.user import User
from agents.biography_team.orchestrator import BiographyOrchestrator

load_dotenv(override=True)

class InterviewSession: 
    
    def __init__(self, user_id: str, interaction_mode: str = 'terminal', enable_voice_output: bool = False, enable_voice_input: bool = False):
        """Initialize the interview session.
        
        Args:
            user_id (str): The user's ID
            interaction_mode (str): How to interact with the user. Options:
                - 'terminal': Terminal-based user interaction
                - 'agent': Automated user agent for testing
                - 'api': API-based interaction (no direct user interface)
            enable_voice_output (bool): Enable voice output
            enable_voice_input (bool): Enable voice input
        """
        self.user_id = user_id
        self.session_note = SessionNote.get_last_session_note(user_id)
        self.session_note.session_id += 1
        self.session_id = self.session_note.session_id
        setup_logger(user_id, self.session_id, console_output_files=["execution_log"])
        
        SessionLogger.log_to_file("execution_log", f"[INIT] Starting interview session for user {user_id}")
        SessionLogger.log_to_file("execution_log", f"[INIT] Session note loaded from the file")
        SessionLogger.log_to_file("execution_log", f"[INIT] Session ID: {self.session_id}")
        
        # User in the interview session
        if interaction_mode == 'agent':
            self.user: User = UserAgent(user_id=user_id, interview_session=self)
        elif interaction_mode == 'terminal':
            self.user: User = User(user_id=user_id, interview_session=self, enable_voice_input=enable_voice_input)
        elif interaction_mode == 'api':
            self.user = None  # No direct user interface for API mode
        else:
            raise ValueError(f"Invalid interaction_mode: {interaction_mode}")
        
        SessionLogger.log_to_file("execution_log", f"[INIT] User instance created with mode: {interaction_mode}")        
        
        # Agents in the interview session
        self.interviewer: Interviewer = Interviewer(config={"user_id": user_id, "tts": {"enabled": enable_voice_output}}, interview_session=self)
        self.memory_manager: MemoryManager = MemoryManager(config={"user_id": user_id}, interview_session=self)
        self.biography_orchestrator = BiographyOrchestrator(config={"user_id": user_id}, interview_session=self)
        
        SessionLogger.log_to_file("execution_log", f"[INIT] Agents initialized: Interviewer, MemoryManager, Biography Orchestrator")
        
        # Chat history
        self.chat_history: list[Message] = []
        self.session_in_progress = False
        
        # Subscriptions - only set up if we have a user instance
        self.subscriptions: Dict[str, List[Participant]] = {
            "Interviewer": [self.memory_manager],
            "User": [self.interviewer, self.memory_manager]
        }
        if self.user:
            self.subscriptions["Interviewer"].append(self.user)
        
        # API participant for handling API responses
        self.api_participant = None
        if interaction_mode == 'api':
            from api.core.api_participant import APIParticipant
            self.api_participant = APIParticipant()
            self.subscriptions["Interviewer"].append(self.api_participant)
        
        # Shutdown signal handler - only for agent mode
        if interaction_mode == 'agent':
            self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._signal_handler)
        SessionLogger.log_to_file("execution_log", f"[INIT] Signal handlers configured")
    
    def _signal_handler(self):
        """Handle shutdown signals"""
        SessionLogger.log_to_file("execution_log", f"[SIGNAL] Shutdown signal received")
        self.session_in_progress = False

    async def notify_participants(self, message: Message):
        """Notify subscribers asynchronously"""
        subscribers = self.subscriptions.get(message.role, [])
        SessionLogger.log_to_file("execution_log", f"[NOTIFY] Notifying {len(subscribers)} subscribers for message from {message.role}")
        
        notification_tasks = [
            subscriber.on_message(message) 
            for subscriber in subscribers
        ]
        await asyncio.gather(*notification_tasks)
        SessionLogger.log_to_file("execution_log", f"[NOTIFY] Completed notifying all subscribers")

    def add_message_to_chat_history(self, role: str, content: str):
        message = Message(
            id=str(uuid.uuid4()),
            role=role, 
            content=content, 
            timestamp=datetime.now()
        )
        self.chat_history.append(message)
        SessionLogger.log_to_file("chat_history", f"{message.role}: {message.content}")
        SessionLogger.log_to_file("execution_log", f"[CHAT_HISTORY] {message.role}'s message has been added to chat history.")
        
        # Schedule async notification
        asyncio.create_task(self.notify_participants(message))

    async def run(self):
        SessionLogger.log_to_file("execution_log", f"[RUN] Starting interview session")
        self.session_in_progress = True
        
        try:
            SessionLogger.log_to_file("execution_log", f"[RUN] Sending initial notification to interviewer")
            await self.interviewer.on_message(None)
            
            while self.session_in_progress:
                await asyncio.sleep(0.1)
                
        except Exception as e:
            SessionLogger.log_to_file("execution_log", f"[RUN] Unexpected error: {str(e)}")
            raise e
        
        finally:
            try:
                with contextlib.suppress(KeyboardInterrupt):
                    await self.update_biography()
                    self.session_note.save()
            except Exception as e:
                SessionLogger.log_to_file("execution_log", f"[RUN] Error during biography update: {str(e)}")
            finally:
                SessionLogger.log_to_file("execution_log", f"[RUN] Interview session completed")
    
    async def update_biography(self):
        """Update biography using the biography team."""
        SessionLogger.log_to_file("execution_log", f"[BIOGRAPHY] Starting biography update")
        
        # Get all memories added during this session
        new_memories = self.memory_manager.get_session_memories()
        
        SessionLogger.log_to_file("execution_log", f"[BIOGRAPHY] Found {len(new_memories)} new memories to process")
        
        try:
            await self.biography_orchestrator.update_biography(new_memories)
            SessionLogger.log_to_file("execution_log", f"[BIOGRAPHY] Successfully updated biography")
        except Exception as e:
            SessionLogger.log_to_file("execution_log", f"[BIOGRAPHY] Error updating biography: {e}", log_level="error")
            raise e
