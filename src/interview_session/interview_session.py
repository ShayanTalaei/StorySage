import asyncio
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, TypedDict
import signal
import contextlib
import concurrent.futures
from dotenv import load_dotenv

from interview_session.session_models import Message, Participant
from agents.interviewer.interviewer import Interviewer, InterviewerConfig, TTSConfig
from agents.note_taker.note_taker import NoteTaker, NoteTakerConfig
from agents.user.user_agent import UserAgent
from session_note.session_note import SessionNote
from utils.logger import SessionLogger, setup_logger
from user.user import User
from agents.biography_team.orchestrator import BiographyOrchestrator
from agents.biography_team.base_biography_agent import BiographyConfig
from memory_bank.memory_bank_vector_db import MemoryBank

load_dotenv(override=True)

class UserConfig(TypedDict, total=False):
    """Configuration for user settings.
    """
    user_id: str
    enable_voice: bool
    biography_style: str

class InterviewConfig(TypedDict, total=False):
    """Configuration for interview settings."""
    enable_voice: bool

class InterviewSession: 
    
    def __init__(self, interaction_mode: str = 'terminal', user_config: UserConfig = {}, interview_config: InterviewConfig = {}):
        """Initialize the interview session.

        Args:
            interaction_mode: How to interact with user - 'terminal', 'agent' (automated), or 'api'
            user_config: User configuration dictionary
                user_id: User identifier (default: 'default_user')
                enable_voice: Enable voice input (default: False)
            interview_config: Interview configuration dictionary
                enable_voice: Enable voice output (default: False)
        """

        # Session setup
        self.user_id = user_config.get("user_id", "default_user")

        # Grabs last session note. This is updated to reflect the new questions for this session.
        self.session_note = SessionNote.get_last_session_note(self.user_id)
        self.memory_bank = MemoryBank.load_from_file(self.user_id)
        self.session_id = self.session_note.increment_session_id()

        # Logs to execution_log
        setup_logger(self.user_id, self.session_id, console_output_files=["execution_log"])
        SessionLogger.log_to_file("execution_log", f"[INIT] Starting interview session for user {self.user_id}")
        SessionLogger.log_to_file("execution_log", f"[INIT] Session ID: {self.session_id}")
        
        # Chat history
        self.chat_history: list[Message] = []

        # Session states signals
        self.interaction_mode = interaction_mode
        self.session_in_progress = True
        self.session_completed = False
        self._biography_updated = False
        
        # Last message timestamp tracking
        self.last_message_time = datetime.now()
        self.timeout_minutes = int(os.getenv("SESSION_TIMEOUT_MINUTES", 10))

        # User in the interview session
        if interaction_mode == 'agent':
            self.user: User = UserAgent(user_id=self.user_id, interview_session=self)
        elif interaction_mode == 'terminal':
            self.user: User = User(user_id=self.user_id, interview_session=self, enable_voice_input=user_config.get("enable_voice", False))
        elif interaction_mode == 'api':
            self.user = None  # No direct user interface for API mode
        else:
            raise ValueError(f"Invalid interaction_mode: {interaction_mode}")
        
        SessionLogger.log_to_file("execution_log", f"[INIT] User instance created with mode: {interaction_mode}")
        
        # Agents in the interview session
        self.interviewer: Interviewer = Interviewer(
            config=InterviewerConfig(
                user_id=self.user_id,
                tts=TTSConfig(enabled=interview_config.get("enable_voice", False))
            ),
            interview_session=self
        )
        self.note_taker: NoteTaker = NoteTaker(
            config=NoteTakerConfig(
                user_id=self.user_id
            ),
            interview_session=self
        )
        self.biography_orchestrator = BiographyOrchestrator(
            config=BiographyConfig(
                user_id=self.user_id,
                biography_style=user_config.get("biography_style", "chronological")
            ),
            interview_session=self
        )
        
        SessionLogger.log_to_file("execution_log", f"[INIT] Agents initialized: Interviewer, Note Taker, Biography Orchestrator")
        
        # Interviewer subscribes to NoteTaker. That is, Notetaker's on_message function is called when Interviewer updates shared chat history.
        # User subscribes to Interviewer and NoteTaker. That is, Interviewer or NoteTaker's on_message function is called when User updates shared chat history.
        self.subscriptions: Dict[str, List[Participant]] = {
            "Interviewer": [self.note_taker],
            "User": [self.interviewer, self.note_taker]
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

    async def _notify_participants(self, message: Message):
        """Notify subscribers asynchronously"""
        # Gets subscribers for the user that sent the message.
        subscribers = self.subscriptions.get(message.role, [])
        SessionLogger.log_to_file("execution_log", f"[NOTIFY] Notifying {len(subscribers)} subscribers for message from {message.role}")
        
        # Use thread pool for parallel execution of notifications
        with concurrent.futures.ThreadPoolExecutor() as pool:
            notification_tasks = [
                pool.submit(lambda s=subscriber: asyncio.run(s.on_message(message)))
                for subscriber in subscribers
            ]
            # Wait for all notifications to complete
            concurrent.futures.wait(notification_tasks)
        SessionLogger.log_to_file("execution_log", f"[NOTIFY] Completed notifying all subscribers")

    def add_message_to_chat_history(self, role: str, content: str):
        """Add a message to the chat history"""
        if not self.session_in_progress:
            return  # Block new messages after session ended
        
        message = Message(
            id=str(uuid.uuid4()),
            role=role, 
            content=content, 
            timestamp=datetime.now()
        )
        self.chat_history.append(message)
        SessionLogger.log_to_file("chat_history", f"{message.role}: {message.content}")
        SessionLogger.log_to_file("execution_log", f"[CHAT_HISTORY] {message.role}'s message has been added to chat history.")
        
        # Only notify if session is still active
        if self.session_in_progress:  
            asyncio.create_task(self._notify_participants(message))
        
        # Update last message time when we receive a message
        if role == "User":
            self.last_message_time = datetime.now()

    async def run(self):
        """Run the interview session"""
        SessionLogger.log_to_file("execution_log", f"[RUN] Starting interview session")
        self.session_in_progress = True
        
        try:
            # Only have interviewer initiate the conversation if not in API mode
            if self.user is not None:
                SessionLogger.log_to_file("execution_log", f"[RUN] Sending initial notification to interviewer by system")
                await self.interviewer.on_message(None)
            
            # Monitor the session for completion and timeout
            while self.session_in_progress or self.note_taker.processing_in_progress:
                await asyncio.sleep(0.1)
                
                # Check for timeout
                if datetime.now() - self.last_message_time > timedelta(minutes=self.timeout_minutes):
                    SessionLogger.log_to_file("execution_log", f"[TIMEOUT] Session timed out after {self.timeout_minutes} minutes of inactivity")
                    self.session_in_progress = False
                    break
                
        except Exception as e:
            SessionLogger.log_to_file("execution_log", f"[RUN] Unexpected error: {str(e)}")
            raise e
        
        finally:
            try:
                # Only update biography if not in API mode and not already updated (API mode handles this separately)
                if self.interaction_mode != 'api' and not self._biography_updated:
                    with contextlib.suppress(KeyboardInterrupt):
                        SessionLogger.log_to_file("execution_log", f"[BIOGRAPHY] Starting biography update automatically in interview session")
                        await self.biography_orchestrator.update_biography()
                        self._biography_updated = True
            except Exception as e:
                SessionLogger.log_to_file("execution_log", f"[RUN] Error during biography update: {str(e)}")
            finally:
                self.session_note.save()
                self.session_completed = True
                SessionLogger.log_to_file("execution_log", f"[RUN] Interview session completed")

    def set_db_session_id(self, db_session_id: int):
        """Set the database session ID"""
        self.db_session_id = db_session_id
    
    def get_db_session_id(self) -> int:
        """Get the database session ID"""
        return self.db_session_id
    
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
    
    def get_session_memories(self):
        """Get all memories added during this session"""
        memories = self.note_taker.get_session_memories()
        SessionLogger.log_to_file("execution_log", f"[BIOGRAPHY] Found {len(memories)} memories")
        return memories

    def mark_biography_updated(self):
        """Mark that the biography has been updated externally (used by API mode)"""
        self._biography_updated = True

    def end_session(self):
        """End the session without triggering biography update"""
        self.session_in_progress = False