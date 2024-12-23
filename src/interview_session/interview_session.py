import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, TypedDict
import signal
import contextlib

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
        self.session_note = SessionNote.get_last_session_note(self.user_id)
        self.session_id = self.session_note.increment_session_id()
        setup_logger(self.user_id, self.session_id, console_output_files=["execution_log"])
        
        # Chat history and session state
        self.chat_history: list[Message] = []
        self.session_in_progress = True
        self.session_completed = False

        SessionLogger.log_to_file("execution_log", f"[INIT] Starting interview session for user {self.user_id}")
        SessionLogger.log_to_file("execution_log", f"[INIT] Session ID: {self.session_id}")
        
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
                user_id=self.user_id,
                followup_interval=3
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
        
        # Subscriptions - only set up if we have a user instance
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

    async def _notify_participants(self, message: Message):
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
        asyncio.create_task(self._notify_participants(message))

    async def run(self):
        SessionLogger.log_to_file("execution_log", f"[RUN] Starting interview session")
        self.session_in_progress = True
        
        try:
            # Only have interviewer initiate the conversation if not in API mode
            if self.user is not None:
                SessionLogger.log_to_file("execution_log", f"[RUN] Sending initial notification to interviewer by system")
                await self.interviewer.on_message(None)
            
            # Monitor the session for completion
            while self.session_in_progress:
                await asyncio.sleep(0.1)
                
        except Exception as e:
            SessionLogger.log_to_file("execution_log", f"[RUN] Unexpected error: {str(e)}")
            raise e
        
        finally:
            try:
                # Update biography and save session note
                with contextlib.suppress(KeyboardInterrupt):
                    await self._update_biography()
            except Exception as e:
                SessionLogger.log_to_file("execution_log", f"[RUN] Error during biography update: {str(e)}")
            finally:
                self.session_note.save()
                self.session_completed = True
                SessionLogger.log_to_file("execution_log", f"[RUN] Interview session completed")
    
    async def _update_biography(self):
        """Update biography using the biography team."""
        SessionLogger.log_to_file("execution_log", f"[BIOGRAPHY] Starting biography update")
        
        # Get all memories added during this session
        new_memories = self.note_taker.get_session_memories()
        
        SessionLogger.log_to_file("execution_log", f"[BIOGRAPHY] Found {len(new_memories)} new memories to process")
        
        try:
            await self.biography_orchestrator.update_biography(new_memories)
            SessionLogger.log_to_file("execution_log", f"[BIOGRAPHY] Successfully updated biography")
        except Exception as e:
            SessionLogger.log_to_file("execution_log", f"[BIOGRAPHY] Error updating biography: {e}", log_level="error")
            raise e
