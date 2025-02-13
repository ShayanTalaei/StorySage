import asyncio
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, TypedDict
import signal
import contextlib
from dotenv import load_dotenv
import time

from interview_session.session_models import Message, MessageType, Participant
from agents.interviewer.interviewer import Interviewer, InterviewerConfig, TTSConfig
from agents.note_taker.note_taker import NoteTaker, NoteTakerConfig
from agents.user.user_agent import UserAgent
from content.session_note.session_note import SessionNote
from utils.feedback import save_feedback_to_csv
from utils.logger import SessionLogger, setup_logger
from interview_session.user.user import User
from agents.biography_team.orchestrator import BiographyOrchestrator
from agents.biography_team.base_biography_agent import BiographyConfig
from content.memory_bank.memory_bank_vector_db import MemoryBankVectorDB
from content.question_bank.question_bank_vector_db import QuestionBankVectorDB
# from content.memory_bank.memory_bank_graph_rag import MemoryBankGraphRAG  # future implementation

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

class BankConfig(TypedDict, total=False):
    """Configuration for memory and question banks."""
    memory_bank_type: str  # "vector_db", "graph_rag", etc.
    question_bank_type: str  # "vector_db", "graph", "semantic", etc.

class InterviewSession: 
    
    def __init__(self, interaction_mode: str = 'terminal', user_config: UserConfig = {}, 
                 interview_config: InterviewConfig = {}, bank_config: BankConfig = {}):
        """Initialize the interview session.

        Args:
            interaction_mode: How to interact with user - 'terminal', 'agent' (automated), or 'api'
            user_config: User configuration dictionary
                user_id: User identifier (default: 'default_user')
                enable_voice: Enable voice input (default: False)
            interview_config: Interview configuration dictionary
                enable_voice: Enable voice output (default: False)
            bank_config: Bank configuration dictionary
                memory_bank_type: Type of memory bank to use ("vector_db" or "graph_rag")
                question_bank_type: Type of question bank to use ("vector_db" or "graph" or "semantic")
        """

        # User setup
        self.user_id = user_config.get("user_id", "default_user")

        # Session note setup
        self.session_note = SessionNote.get_last_session_note(self.user_id)
        self.session_id = self.session_note.session_id + 1

        # Memory bank setup
        memory_bank_type = bank_config.get("memory_bank_type", "vector_db")
        if memory_bank_type == "vector_db":
            self.memory_bank = MemoryBankVectorDB.load_from_file(self.user_id)
        else:
            raise ValueError(f"Unknown memory bank type: {memory_bank_type}")
        
        # Question bank setup
        question_bank_type = bank_config.get("question_bank_type", "vector_db")
        if question_bank_type == "vector_db":
            self.question_bank = QuestionBankVectorDB.load_from_file(self.user_id)
        else:
            raise ValueError(f"Unknown question bank type: {question_bank_type}")
        
        # Logger setup
        setup_logger(self.user_id, self.session_id, console_output_files=["execution_log"])
        SessionLogger.log_to_file("execution_log", f"[INIT] Interview session initialized")
        SessionLogger.log_to_file("execution_log", f"[INIT] User ID: {self.user_id}")
        SessionLogger.log_to_file("execution_log", f"[INIT] Session ID: {self.session_id}")
        
        # Chat history
        self.chat_history: list[Message] = []

        # Session states signals
        self.interaction_mode = interaction_mode
        self.session_in_progress = True
        self.session_completed = False
        
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
        
        # Subscriptions of participants to each other
        self.subscriptions: Dict[str, List[Participant]] = {
            "Interviewer": [self.note_taker], # Note-taker subscribes to Interviewer. That is, Note-taker's on_message function is called when Interviewer updates shared chat history.
            "User": [self.interviewer, self.note_taker] # Interviewer + Note-taker subscribes to User. That is, Interviewer or NoteTaker's on_message function is called when User updates shared chat history.
        }
        
        # API participant for terminal interaction
        if self.user:
            self.subscriptions["Interviewer"].append(self.user)
        
        # API participant for backend API interaction
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
        
        # Create independent tasks for each subscriber
        tasks = []
        for sub in subscribers:
            task = asyncio.create_task(sub.on_message(message))
            tasks.append(task)        
        # Allow tasks to run concurrently without waiting for each other
        await asyncio.sleep(0)  # Explicitly yield control

    def add_message_to_chat_history(self, role: str, content: str = "", message_type: str = MessageType.CONVERSATION):
        """Add a message to the chat history"""

        # Set fixed content for skip and like messages
        if message_type == MessageType.SKIP:
            content = "Skip the question"
        elif message_type == MessageType.LIKE:
            content = "Like the question"
        
        message = Message(
            id=str(uuid.uuid4()),
            type=message_type,
            role=role, 
            content=content, 
            timestamp=datetime.now(),
        )

        # Save feedback to into a separate file
        if message_type != MessageType.CONVERSATION:
            save_feedback_to_csv(self.chat_history[-1], message, self.user_id, self.session_id)
        
        # Notify participants if message is a skip or conversation
        if message_type == MessageType.SKIP or message_type == MessageType.CONVERSATION:
            self.chat_history.append(message)
            asyncio.create_task(self._notify_participants(message))
        
        # Update last message time when we receive a message
        if role == "User":
            self.last_message_time = datetime.now()
        
        SessionLogger.log_to_file("chat_history", f"{message.role}: {message.content}")
        SessionLogger.log_to_file("execution_log", f"[CHAT_HISTORY] {message.role}'s message has been added to chat history.")    

    async def run(self):
        """Run the interview session"""
        SessionLogger.log_to_file("execution_log", f"[RUN] Starting interview session")
        self.session_in_progress = True
        
        try:
            # Only have interviewer initiate the conversation if not in API mode
            if self.user is not None:
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
                # Update biography (API mode handles this separately)
                if self.interaction_mode != 'api':
                    with contextlib.suppress(KeyboardInterrupt):
                        SessionLogger.log_to_file("execution_log", f"[BIOGRAPHY] Starting biography update automatically in interview session")
                        await self.biography_orchestrator.update_biography(selected_topics=[])

                # Wait for biography update to complete if it's in progress
                start_time = time.time()
                while self.biography_orchestrator.update_in_progress:
                    await asyncio.sleep(0.1)
                    if time.time() - start_time > 300: # 5 minutes timeout
                        SessionLogger.log_to_file("execution_log", f"[BIOGRAPHY] Timeout waiting for biography update")
                        break

            except Exception as e:
                SessionLogger.log_to_file("execution_log", f"[RUN] Error during biography update: {str(e)}")
            finally:
                self.memory_bank.save_to_file(self.user_id)
                SessionLogger.log_to_file("execution_log", f"[COMPLETED] Memory bank saved")
                self.question_bank.save_to_file(self.user_id)
                SessionLogger.log_to_file("execution_log", f"[COMPLETED] Question bank saved")
                self.session_completed = True
                SessionLogger.log_to_file("execution_log", f"[COMPLETED] Session completed")

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
    
    def _signal_handler(self):
        """Handle shutdown signals"""
        SessionLogger.log_to_file("execution_log", f"[SIGNAL] Shutdown signal received")
        # Set flag to stop accepting new messages
        self.session_in_progress = False

    async def get_session_memories(self):
        """Get all memories added during this session"""
        return await self.note_taker.get_session_memories()

    def end_session(self):
        """End the session without triggering biography update"""
        self.session_in_progress = False