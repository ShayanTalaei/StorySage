from typing import Optional, Dict, AsyncIterator
import asyncio
from datetime import datetime

from interview_session.session_models import Participant, Message

class APIParticipant(Participant):
    def __init__(self, title: str = "APIParticipant"):
        super().__init__(title=title, interview_session=None)
        self.response_queue: asyncio.Queue = asyncio.Queue()
        self.last_message: Optional[Message] = None
    
    async def on_message(self, message: Message):
        """Receive message from the interview session"""
        self.last_message = message
        await self.response_queue.put(message)
    
    async def wait_for_response(self, timeout: float = 10.0) -> Optional[Message]:
        """Wait for a response from the interview session"""
        try:
            return await asyncio.wait_for(self.response_queue.get(), timeout)
        except asyncio.TimeoutError:
            return None 