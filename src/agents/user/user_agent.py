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
        
        # Load profile background
        profile_path = os.path.join(os.getenv("USER_AGENT_PROFILES_DIR"), f"{self.user_id}/{self.user_id}.md")
        with open(profile_path, 'r') as f:
            self.profile_background = f.read()
            
        # Load conversational style
        conv_style_path = os.path.join(os.getenv("USER_AGENT_PROFILES_DIR"), f"{self.user_id}/conversation.md")
        with open(conv_style_path, 'r') as f:
            self.conversational_style = f.read()
    
    async def on_message(self, message: Message):
        """Handle incoming messages by generating a response and notifying the interview session"""
        if not message:  # Skip if no message (initial notification)
            return
            
        # Add the interviewer's message to our event stream
        self.add_event(sender=message.role, tag="message", content=message.content)
        
        # First, determine if user wants to respond
        prompt = self.get_prompt(prompt_type="decide_to_respond")
        self.add_event(sender=self.name, tag="decide_prompt", content=prompt)
        decide_response = await self.call_engine_async(prompt)
        self.add_event(sender=self.name, tag="decide_response", content=decide_response)
        
        # Extract the decision and reasoning
        wants_to_respond, wants_to_respond_reasoning = self._extract_decision(decide_response)
        
        if wants_to_respond:
            # Generate detailed response using LLM
            response_prompt = self.get_prompt(prompt_type="respond_to_question")
            self.add_event(sender=self.name, tag="response_prompt", content=response_prompt)
            full_response = await self.call_engine_async(response_prompt)
            self.add_event(sender=self.name, tag="llm_response", content=full_response)
            
            # Extract just the <response> content to send to chat history
            response_content, _ = self._extract_response(full_response)
            self.add_event(sender=self.name, tag="message", content=response_content)

            if response_content:
                self.interview_session.add_message_to_chat_history(role=self.title, content=response_content, message_type="conversation")
        else:
            # Add generic deflection message to chat history
            # Change message type so this can be loged
            deflection_msg = "Let's move on to the next question."
            self.add_event(sender=self.name, tag="message", content=deflection_msg)
            self.interview_session.add_message_to_chat_history(role=self.title, content=deflection_msg, message_type="feedback")
    def get_prompt(self, prompt_type: str) -> str:
        """Get the formatted prompt for the LLM"""
        from agents.user.prompts import get_prompt
        
        return get_prompt(prompt_type).format(
            profile_background = self.profile_background,
            conversational_style = self.conversational_style,
            chat_history = self.get_event_stream_str([{"tag": "message"}])
        )
    
    def _extract_response(self, full_response: str) -> tuple[str, str]:
        """Extract the content between <response_content> and <thinking> tags"""
        response_match = re.search(r'<response_content>(.*?)</response_content>', full_response, re.DOTALL)
        thinking_match = re.search(r'<thinking>(.*?)</thinking>', full_response, re.DOTALL)
        
        response = response_match.group(1).strip() if response_match else full_response
        thinking = thinking_match.group(1).strip() if thinking_match else ""
        
        return response, thinking
