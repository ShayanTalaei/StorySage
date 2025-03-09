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
from utils.data_process import save_feedback_to_csv
from utils.logger.session_logger import SessionLogger, setup_logger
from utils.logger.evaluation_logger import EvaluationLogger
from interview_session.user.user import User
from agents.biography_team.orchestrator import BiographyOrchestrator
from agents.biography_team.base_biography_agent import BiographyConfig
from content.memory_bank.memory_bank_vector_db import VectorMemoryBank
from content.memory_bank.memory import Memory
from content.question_bank.question_bank_vector_db import QuestionBankVectorDB
from interview_session.prompts.conversation_summerize import summarize_conversation


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
    historical_question_bank_type: str  # "vector_db", "graph", "semantic", etc.


class InterviewSession:

    def __init__(self, interaction_mode: str = 'terminal', user_config: UserConfig = {},
                 interview_config: InterviewConfig = {}, bank_config: BankConfig = {}):
        """Initialize the interview session.

        Args:
            interaction_mode: How to interact with user 
                Options: 'terminal', 'agent', or 'api'
            user_config: User configuration dictionary
                user_id: User identifier (default: 'default_user')
                enable_voice: Enable voice input (default: False)
            interview_config: Interview configuration dictionary
                enable_voice: Enable voice output (default: False)
            bank_config: Bank configuration dictionary
                memory_bank_type: Type of memory bank 
                    Options: "vector_db", etc.
                historical_question_bank_type: Type of question bank 
                    Options: "vector_db", etc.
        """

        # User setup
        self.user_id = user_config.get("user_id", "default_user")

        # Session note setup
        self.session_note = SessionNote.get_last_session_note(self.user_id)
        self.session_id = self.session_note.session_id + 1

        # Memory bank setup
        memory_bank_type = bank_config.get("memory_bank_type", "vector_db")
        if memory_bank_type == "vector_db":
            self.memory_bank = VectorMemoryBank.load_from_file(self.user_id)
        else:
            raise ValueError(f"Unknown memory bank type: {memory_bank_type}")

        # Question bank setup
        historical_question_bank_type = \
            bank_config.get("historical_question_bank_type", "vector_db")
        if historical_question_bank_type == "vector_db":
            self.historical_question_bank = \
                QuestionBankVectorDB.load_from_file(
                self.user_id)
            self.proposed_question_bank = QuestionBankVectorDB()
        else:
            raise ValueError(
                f"Unknown question bank type: {historical_question_bank_type}")

        # Logger setup
        setup_logger(self.user_id, self.session_id,
                     console_output_files=["execution_log"])
        EvaluationLogger.setup_logger(self.user_id, self.session_id)

        # Chat history
        self.chat_history: list[Message] = []

        # Session states signals
        self._interaction_mode = interaction_mode
        self.session_in_progress = True
        self.session_completed = False
        self._session_timeout = False

        # Biography auto-update states
        self.auto_biography_update_in_progress = False
        self.memory_threshold = int(
            os.getenv("MEMORY_THRESHOLD_FOR_UPDATE", 12))
        
        # Conversation summary for auto-updates
        self.conversation_summary = ""
        
        # Counter for user messages to trigger biography update check
        self._user_message_count = 0
        self._check_interval = max(1, self.memory_threshold // 3)

        # Last message timestamp tracking for session timeout
        self._last_message_time = datetime.now()
        self.timeout_minutes = int(os.getenv("SESSION_TIMEOUT_MINUTES", 10))

        # Response latency tracking for evaluation
        self._last_user_message = None

        # User in the interview session
        if interaction_mode == 'agent':
            self.user: User = UserAgent(
                user_id=self.user_id, interview_session=self)
        elif interaction_mode == 'terminal':
            self.user: User = User(user_id=self.user_id, interview_session=self,
                                   enable_voice_input=user_config \
                                   .get("enable_voice", False))
        elif interaction_mode == 'api':
            self.user = None  # No direct user interface for API mode
        else:
            raise ValueError(f"Invalid interaction_mode: {interaction_mode}")

        # Agents in the interview session
        self._interviewer: Interviewer = Interviewer(
            config=InterviewerConfig(
                user_id=self.user_id,
                tts=TTSConfig(enabled=interview_config.get(
                    "enable_voice", False))
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
                biography_style=user_config.get(
                    "biography_style", "chronological")
            ),
            interview_session=self
        )

        # Subscriptions of participants to each other
        self._subscriptions: Dict[str, List[Participant]] = {
            # Subscribers of Interviewer: Note-taker and User (in following code)
            "Interviewer": [self.note_taker],
            # Subscribers of User: Interviewer and Note-taker
            "User": [self._interviewer, self.note_taker]
        }

        # User participant for terminal interaction
        if self.user:
            self._subscriptions["Interviewer"].append(self.user)

        # User API participant for backend API interaction
        self.api_participant = None
        if interaction_mode == 'api':
            from api.core.api_participant import APIParticipant
            self.api_participant = APIParticipant()
            self._subscriptions["Interviewer"].append(self.api_participant)

        # Shutdown signal handler - only for agent mode
        if interaction_mode == 'agent':
            self._setup_signal_handlers()
        
        SessionLogger.log_to_file(
            "execution_log", f"[INIT] Interview session initialized")
        SessionLogger.log_to_file(
            "execution_log", f"[INIT] User ID: {self.user_id}")
        SessionLogger.log_to_file(
            "execution_log", f"[INIT] Session ID: {self.session_id}")


    async def _notify_participants(self, message: Message):
        """Notify subscribers asynchronously"""
        # Gets subscribers for the user that sent the message.
        subscribers = self._subscriptions.get(message.role, [])
        SessionLogger.log_to_file(
            "execution_log", 
            (
                f"[NOTIFY] Notifying {len(subscribers)} subscribers "
                f"for message from {message.role}"
            )
        )

        # Create independent tasks for each subscriber
        tasks = []
        for sub in subscribers:
            if self.session_in_progress:
                task = asyncio.create_task(sub.on_message(message))
                tasks.append(task)
        # Allow tasks to run concurrently without waiting for each other
        await asyncio.sleep(0)  # Explicitly yield control
        
        # Check if we need to trigger a biography update
        if message.role == "User":
            self._user_message_count += 1
            if (self._user_message_count % self._check_interval == 0 and 
                not self.auto_biography_update_in_progress):
                asyncio.create_task(self._check_and_trigger_biography_update())

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

        # Save feedback into a file
        if message_type != MessageType.CONVERSATION:
            save_feedback_to_csv(
                self.chat_history[-1], message, self.user_id, self.session_id)

        # Save response latency into a file
        if message_type == MessageType.CONVERSATION:
            if role == "User":
                # Store user message for latency calculation
                self._last_user_message = message
            elif role == "Interviewer" and self._last_user_message is not None:
                # Calculate and log latency when interviewer responds
                self._log_response_latency(self._last_user_message, message)
                self._last_user_message = None

        # Notify participants if message is a skip or conversation
        if message_type == MessageType.SKIP or \
              message_type == MessageType.CONVERSATION:
            self.chat_history.append(message)
            SessionLogger.log_to_file(
                "chat_history", f"{message.role}: {message.content}")
            asyncio.create_task(self._notify_participants(message))

        # Update last message time when we receive a message
        if role == "User":
            self._last_message_time = datetime.now()

        SessionLogger.log_to_file(
            "execution_log", 
            (
                f"[CHAT_HISTORY] {message.role}'s message has been added "
                f"to chat history."
            )
        )

    async def run(self):
        """Run the interview session"""
        SessionLogger.log_to_file(
            "execution_log", f"[RUN] Starting interview session")
        self.session_in_progress = True

        # In-interview Processing
        try:
            # Interviewer initiate the conversation (if not in API mode)
            if self.user is not None:
                await self._interviewer.on_message(None)

            # Monitor the session for completion and timeout
            while self.session_in_progress or self.note_taker.processing_in_progress:
                await asyncio.sleep(0.1)

                # Check for timeout
                if datetime.now() - self._last_message_time \
                        > timedelta(minutes=self.timeout_minutes):
                    SessionLogger.log_to_file(
                        "execution_log", 
                        (
                            f"[TIMEOUT] Session timed out after "
                            f"{self.timeout_minutes} minutes of inactivity"
                        )
                    )
                    self.session_in_progress = False
                    self._session_timeout = True
                    break

        except Exception as e:
            SessionLogger.log_to_file(
                "execution_log", f"[RUN] Unexpected error: {str(e)}")
            raise e

        # Post-interview Processing
        finally:
            try:
                self.session_in_progress = False

                # Update biography (API mode handles this separately)
                if self._interaction_mode != 'api' or self._session_timeout:
                    with contextlib.suppress(KeyboardInterrupt):
                        SessionLogger.log_to_file(
                            "execution_log", 
                            (
                                f"[BIOGRAPHY] Trigger final biography update. "
                                f"Waiting for note taker to finish processing..."
                            )
                        )
                        await self.biography_orchestrator \
                            .update_biography_and_notes(selected_topics=[])

                # Wait for biography update to complete if it's in progress
                start_time = time.time()
                while (self.biography_orchestrator.biography_update_in_progress or 
                       self.biography_orchestrator.session_note_update_in_progress):
                    await asyncio.sleep(0.1)
                    if time.time() - start_time > 300:  # 5 minutes timeout
                        SessionLogger.log_to_file(
                            "execution_log", 
                            (
                                f"[BIOGRAPHY] Timeout waiting for biography update"
                            )
                        )
                        break

            except Exception as e:
                SessionLogger.log_to_file(
                    "execution_log", f"[RUN] Error during biography update: \
                          {str(e)}")
            finally:
                # Save memory bank
                self.memory_bank.save_to_file(self.user_id)
                SessionLogger.log_to_file(
                    "execution_log", f"[COMPLETED] Memory bank saved")
                
                # Save historical question bank
                self.historical_question_bank.save_to_file(self.user_id)
                SessionLogger.log_to_file(
                    "execution_log", f"[COMPLETED] Question bank saved")
                
                # Log conversation statistics
                self.log_conversation_statistics()
                SessionLogger.log_to_file(
                    "execution_log", f"[COMPLETED] Conversation statistics logged")
                
                self.session_completed = True
                SessionLogger.log_to_file(
                    "execution_log", f"[COMPLETED] Session completed")

    async def get_session_memories(self, include_processed=True) -> List[Memory]:
        """Get memories added during this session
        
        Args:
            include_processed: If True, returns all memories from the session
                              If False, returns only the unprocessed memories
        """
        return await self.note_taker.get_session_memories(
            clear_processed=False, 
            wait_for_processing=True,
            include_processed=include_processed
        )

    async def _check_and_trigger_biography_update(self):
        """Check if we have enough memories to trigger a biography update"""
        # Skip if biography update already in progress or session not in progress
        if self.auto_biography_update_in_progress or \
           not self.session_in_progress or \
           self.biography_orchestrator.biography_update_in_progress:
            return
            
        # Get current memory count without clearing or waiting
        memories = await self.note_taker \
            .get_session_memories(clear_processed=False,
                                   wait_for_processing=False)
        
        # Check if we've reached the threshold
        if len(memories) >= self.memory_threshold:
            SessionLogger.log_to_file(
                "execution_log",
                f"[AUTO-UPDATE] Triggering biography update "
                f"with {len(memories)} memories"
            )
            
            try:
                self.auto_biography_update_in_progress = True
                
                # Generate a summary of recent conversation
                await self._update_conversation_summary()
                
                # Get memories and clear them from the note taker
                memories_to_process = \
                    await self.note_taker.get_session_memories(
                        clear_processed=True, wait_for_processing=False)
                
                # Update biography with these memories and the conversation summary
                await self.biography_orchestrator.update_biography_with_memories(
                    memories_to_process,
                    is_auto_update=True
                )
                
                SessionLogger.log_to_file(
                    "execution_log",
                    f"[AUTO-UPDATE] Biography update completed "
                    f"for {len(memories_to_process)} memories"
                )
                
            except Exception as e:
                SessionLogger.log_to_file(
                    "execution_log", 
                    f"[AUTO-UPDATE] Error during biography update: {str(e)}"
                )
            finally:
                self.auto_biography_update_in_progress = False
    
    async def _update_conversation_summary(self):
        """Generate a summary of recent conversation messages"""
        
        # Extract recent messages from chat history
        recent_messages: List[Message] = []
        for msg in self.chat_history[-self.note_taker._max_events_len:]:
            if msg.type == MessageType.CONVERSATION:
                recent_messages.append(msg)
        
        # Generate summary if we have messages
        if recent_messages:
            self.conversation_summary = \
                summarize_conversation(recent_messages)

    def end_session(self):
        """End the session without triggering biography update"""
        self.session_in_progress = False

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._signal_handler)

    def _signal_handler(self):
        """Handle shutdown signals"""
        self.session_in_progress = False
        SessionLogger.log_to_file(
            "execution_log", f"[SIGNAL] Shutdown signal received")
        SessionLogger.log_to_file(
            "execution_log", f"[SIGNAL] Waiting for interview session to finish...")
    
    def set_db_session_id(self, db_session_id: int):
        """Set the database session ID. Used for server mode"""
        self.db_session_id = db_session_id

    def get_db_session_id(self) -> int:
        """Get the database session ID. Used for server mode"""
        return self.db_session_id
        
    def _log_response_latency(self, user_message: Message, response_message: Message):
        """Log the latency between user message and system response.
        
        Args:
            user_message: The user's message
            response_message: The system's response message
        """
        # Get the evaluation logger
        eval_logger = EvaluationLogger.get_current_logger()
        
        # Get user message length
        user_message_length = len(user_message.content)
        
        # Log the latency
        eval_logger.log_response_latency(
            message_id=user_message.id,
            user_message_timestamp=user_message.timestamp,
            response_timestamp=response_message.timestamp,
            user_message_length=user_message_length
        )

    def log_conversation_statistics(self):
        """Log statistics about the conversation."""
        # Count turns
        total_turns = len(self.chat_history)
        
        # Count characters instead of tokens
        user_chars = 0
        system_chars = 0
        
        for message in self.chat_history:
            if message.role == "User":
                user_chars += len(message.content)
            else:
                system_chars += len(message.content)
        
        total_chars = user_chars + system_chars
        
        # Calculate conversation duration
        start_time = getattr(self, 'start_time', None)
        if start_time:
            conversation_duration = (datetime.now() - start_time).total_seconds()
        else:
            # Use first message timestamp as fallback
            if self.chat_history:
                first_message_time = self.chat_history[0].timestamp
                conversation_duration = (datetime.now() - first_message_time).total_seconds()
            else:
                conversation_duration = 0
        
        # Log statistics
        eval_logger = EvaluationLogger.setup_logger(self.user_id, self.session_id)
        eval_logger.log_conversation_statistics(
            total_turns=total_turns,
            total_chars=total_chars,
            user_chars=user_chars,
            system_chars=system_chars,
            conversation_duration=conversation_duration
        )
        
        SessionLogger.log_to_file(
            "execution_log", 
            f"[STATS] Conversation statistics logged"
        )