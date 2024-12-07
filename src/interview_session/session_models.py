from datetime import datetime
from pydantic import BaseModel
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession

class Message(BaseModel):
    id: str
    role: str
    content: str
    timestamp: datetime

class Participant:
    def __init__(self, title: str, interview_session: 'InterviewSession'):
        self.title: str = title
        self.interview_session = interview_session
    
    async def on_message(self, message: Message):
        """Handle new message notification"""
        pass