import os
import json
import dotenv
import re
from agents.base_agent import BaseAgent
from user.user import User
from interview_session.session_models import Message
dotenv.load_dotenv(override=True)

class UserAgent(BaseAgent, User):
    def __init__(self, user_id: str, interview_session, config: dict = None):
        BaseAgent.__init__(self, name="UserAgent", description="Agent that plays the role of the user", config=config)
        User.__init__(self, user_id=user_id, interview_session=interview_session)
        
        profile_path = os.path.join(os.getenv("USER_AGENT_PROFILES_DIR"), f"{self.user_id}.md")
        with open(profile_path, 'r') as f:
            self.profile_background = f.read()
    
    async def on_message(self, message: Message):
        """Handle incoming messages by generating a response and notifying the interview session"""
        if not message:  # Skip if no message (initial notification)
            return
            
        # Add the interviewer's message to our event stream
        self.add_event(sender=message.role, tag="message", content=message.content)
        
        # Generate response using LLM
        prompt = self.get_prompt()
        self.add_event(sender=self.name, tag="prompt", content=prompt)
        full_response = await self.call_engine_async(prompt)
        self.add_event(sender=self.name, tag="llm_response", content=full_response)
        
        # Extract just the <response> content to send to chat history
        response_content = self._extract_response(full_response)
        self.add_event(sender=self.name, tag="message", content=response_content)

        if response_content:
            self.interview_session.add_message_to_chat_history(role=self.title, content=response_content)
    
    def get_prompt(self):
        """Get the formatted prompt for the LLM"""
        from agents.user.prompts import get_prompt
        
        return get_prompt().format(
            profile_background=self.profile_background,
            chat_history=self.get_event_stream_str([{"tag": "message"}])
        )
    
    def _extract_response(self, full_response: str) -> str:
        """Extract the content between <response_content> tags"""
        response_match = re.search(r'<response_content>(.*?)</response_content>', full_response, re.DOTALL)
        if response_match:
            return response_match.group(1).strip()
        return full_response  # Fallback to full response if no tags found
