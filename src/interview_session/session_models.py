from datetime import datetime
from pydantic import BaseModel
from typing import Optional
import asyncio

class Message(BaseModel):
    id: str
    role: str
    content: str
    timestamp: datetime

class Participant:
    def __init__(self, title, interview_session):
        self.title: str = title
        self.interview_session = interview_session
    
    async def on_message(self, message: Message):
        """Handle new message notification"""
        pass