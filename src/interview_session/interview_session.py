import asyncio
import os
import logging
import uuid
from datetime import datetime
from typing import Dict, List
from pathlib import Path

from dotenv import load_dotenv

from interview_session.session_models import Message, Participant
from agents.interviewer.interviewer import Interviewer
from agents.memory_manager.memory_manager import MemoryManager
from agents.user.user_agent import UserAgent
from session_note.session_note import SessionNote
from agents.biographer.biographer import Biographer
from utils.logger import SessionLogger, setup_logger
from user.user import User

load_dotenv(override=True)

class InterviewSession: 
    
    def __init__(self, user_id: str, user_agent: bool = False):
        self.user_id = user_id
        self.session_note = SessionNote.get_last_session_note(user_id)
        self.session_id = self.session_note.session_id
        setup_logger(user_id, self.session_id, console_output_files=["execution_log"])
        
        SessionLogger.log_to_file("execution_log", f"[INIT] Starting interview session for user {user_id}")
        SessionLogger.log_to_file("execution_log", f"[INIT] Session ID: {self.session_id}")
        
        # User in the interview session
        if user_agent:
            self.user: User = UserAgent(user_id=user_id, interview_session=self)
        else:
            self.user: User = User(user_id=user_id, interview_session=self)
        SessionLogger.log_to_file("execution_log", f"[INIT] User instance created")
        
        # Session notes
        self.session_note: SessionNote = SessionNote.get_last_session_note(user_id)
        SessionLogger.log_to_file("execution_log", f"[INIT] Session note loaded from the file")
        
        # Agents in the interview session
        self.interviewer: Interviewer = Interviewer(config={"user_id": user_id}, interview_session=self)
        self.memory_manager: MemoryManager = MemoryManager(config={"user_id": user_id}, interview_session=self)
        SessionLogger.log_to_file("execution_log", f"[INIT] Agents initialized: Interviewer, MemoryManager")
        # self.biographer: Biographer = Biographer(config={"user_id": user_id}, interview_session=self)
        
        self.chat_history: list[Message] = []
        self.session_in_progress = False
        
        self.subscriptions: Dict[str, List[Participant]] = {
            "Interviewer": [self.user, self.memory_manager],
            "User": [self.interviewer, self.memory_manager]
        }

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
        
        SessionLogger.log_to_file("execution_log", f"[RUN] Sending initial notification to interviewer")
        await self.interviewer.on_message(None)  # Starting the interview session with the interviewer
        
        while self.session_in_progress:
            await asyncio.sleep(0.1)  # Prevent CPU hogging
            
        SessionLogger.log_to_file("execution_log", f"[RUN] Interview session completed")
        
    def update_biography(self, session_summary: str):
        # session_notes: SessionNote = self.biographer.workout(session_summary)
        # session_notes.save()
        pass
