import os
import dotenv
import re
from agents.base_agent import BaseAgent
from interview_session.user.user import User
from interview_session.session_models import Message
from interview_session.session_models import MessageType
dotenv.load_dotenv(override=True)


class UserAgent(BaseAgent, User):
    def __init__(self, user_id: str, interview_session, config: dict = None):
        BaseAgent.__init__(
            self, name="UserAgent", description="Agent that plays the role of the user", config=config)
        User.__init__(self, user_id=user_id,
                      interview_session=interview_session)

        # Load profile background
        profile_path = os.path.join(
            os.getenv("USER_AGENT_PROFILES_DIR"), f"{user_id}/{user_id}.md")
        with open(profile_path, 'r') as f:
            self.profile_background = f.read()

        # Load conversational style
        conv_style_path = os.path.join(
            os.getenv("USER_AGENT_PROFILES_DIR"), f"{user_id}/conversation.md")
        with open(conv_style_path, 'r') as f:
            self.conversational_style = f.read()

    async def on_message(self, message: Message):
        """Handle incoming messages by generating a response and notifying the interview session"""
        if not message or not self.interview_session.session_in_progress:
            return

        # Add the interviewer's message to our event stream
        self.add_event(sender=message.role, tag="message",
                       content=message.content)
        # Score the interviewer's question for potential feedback
        score_prompt = self.get_prompt(prompt_type="score_question")
        self.add_event(sender=self.name,
                       tag="score_question_prompt", content=score_prompt)

        score_response = await self.call_engine_async(score_prompt)
        self.add_event(sender=self.name,
                       tag="score_question_response", content=score_response)

        # # Extract the score and reasoning
        self.question_score, self.question_score_reasoning = self._extract_response(
            score_response)

        prompt = self.get_prompt(prompt_type="respond_to_question")
        self.add_event(sender=self.name,
                       tag="respond_to_question_prompt", content=prompt)

        response = await self.call_engine_async(prompt)
        self.add_event(sender=self.name,
                       tag="respond_to_question_response", content=response)

        response_content, response_reasoning = self._extract_response(response)

        wants_to_respond = response_content != "SKIP"

        if wants_to_respond:
            # Generate detailed response using LLM

            # Extract just the <response> content to send to chat history
            self.add_event(sender=self.name, tag="message",
                           content=response_content)
            self.interview_session.add_message_to_chat_history(
                role=self.title, content=response_reasoning, message_type=MessageType.FEEDBACK)
            self.interview_session.add_message_to_chat_history(
                role=self.title, content=response_content, message_type=MessageType.CONVERSATION)

        else:
            # We SKIP the response and log a feedback message
            self.interview_session.add_message_to_chat_history(
                role=self.title, content=response_reasoning, message_type=MessageType.FEEDBACK)
            self.interview_session.add_message_to_chat_history(
                role=self.title, message_type=MessageType.SKIP)

    def get_prompt(self, prompt_type: str) -> str:
        """Get the formatted prompt for the LLM"""
        from agents.user.prompts import get_prompt

        if prompt_type == "score_question":
            return get_prompt(prompt_type).format(
                profile_background=self.profile_background,
                conversational_style=self.conversational_style,
                chat_history=self.get_event_stream_str([{"tag": "message"}])
            )
        elif prompt_type == "respond_to_question":
            return get_prompt(prompt_type).format(
                profile_background=self.profile_background,
                conversational_style=self.conversational_style,
                score=self.question_score,
                score_reasoning=self.question_score_reasoning,
                chat_history=self.get_event_stream_str([{"tag": "message"}])
            )

    def _extract_response(self, full_response: str) -> tuple[str, str]:
        """Extract the content between <response_content> and <thinking> tags"""
        response_match = re.search(
            r'<response_content>(.*?)</response_content>', full_response, re.DOTALL)
        thinking_match = re.search(
            r'<thinking>(.*?)</thinking>', full_response, re.DOTALL)

        response = response_match.group(
            1).strip() if response_match else full_response
        thinking = thinking_match.group(1).strip() if thinking_match else ""
        return response, thinking
