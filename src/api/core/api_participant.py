from typing import Optional
import asyncio

from interview_session.session_models import Participant, Message

class APIParticipant(Participant):
    """API participant for the interview session"""
    def __init__(self, title: str = "APIParticipant"):
        super().__init__(title=title, interview_session=None)
        self.response_queue: asyncio.Queue = asyncio.Queue()
        self.last_message: Optional[Message] = None
    
    async def on_message(self, message: Message):
        """Receive message from the interview session"""
        self.last_message = message
        await self.response_queue.put(message)
    
    async def wait_for_response(self, timeout: float = 60.0) -> Optional[Message]:
        """Wait for a response from the interview session.
        
        Args:
            timeout (float): Maximum time to wait for response in seconds. Defaults to 60 seconds.
            
        Returns:
            Optional[Message]: The response message if received within timeout, None otherwise.
        """
        try:
            self._clear_queue()
            response = await asyncio.wait_for(self.response_queue.get(), timeout)
            
            return response
        except asyncio.TimeoutError:
            return None
    
    def _clear_queue(self):
        """Clear all messages from the queue"""
        while not self.response_queue.empty():
            try:
                self.response_queue.get_nowait()
            except asyncio.QueueEmpty:
                break