import asyncio
import os
import dotenv
import re
import json
from agents.base_agent import BaseAgent
from interview_session.user.user import User
from interview_session.session_models import Message
from interview_session.session_models import MessageType
from content.session_note.session_note import SessionNote
from utils.logger.session_logger import SessionLogger
dotenv.load_dotenv(override=True)


class UserAgent(BaseAgent, User):
    def __init__(self, user_id: str, interview_session, config: dict = None):
        config["model_name"] = "gpt-4o" # Always use gpt-4o for user agent
        BaseAgent.__init__(
            self, name="UserAgent", 
            description="Agent that plays the role of the user", config=config)
        User.__init__(self, user_id=user_id,
                      interview_session=interview_session)

        # Load profile background
        profile_path = os.path.join(
            os.getenv("USER_AGENT_PROFILES_DIR"), f"{user_id}/{user_id}.md")
        with open(profile_path, 'r') as f:
            self.profile_background = f.read()
        
        # Load topics and advance to next topic
        topics_path = os.path.join(
            os.getenv("USER_AGENT_PROFILES_DIR"), f"{user_id}/topics.json")
        if not os.path.exists(topics_path):
            raise ValueError(
                f"Topics file not found: {topics_path}\n"
                f"Please run: python src/utils/topic_extractor.py --user_id {user_id}"
            )
            
        with open(topics_path, 'r') as f:
            topics_data = json.load(f)
            topics = topics_data["topics"]
            
            # Set the topic for this session
            current_topic_index = self.interview_session.session_id - 1
            self.current_topic = topics[current_topic_index]

            SessionLogger.log_to_file(
                "execution_log",
                f"Current topic of {user_id}: {self.current_topic}"
            )
        
        # Get historical session summaries
        self.session_history = SessionNote.get_historical_session_summaries(user_id)

        # Load conversational style
        conv_style_path = os.path.join(
            os.getenv("USER_AGENT_PROFILES_DIR"), f"{user_id}/conversation.md")
        with open(conv_style_path, 'r') as f:
            self.conversational_style = f.read()

    async def on_message(self, message: Message):
        """Handle incoming messages by generating a response and notifying 
        the interview session"""
        if not message:
            return

        # Add the interviewer's message to our event stream
        self.add_event(sender=message.role, tag="message",
                       content=message.content)
        
        # Score the interviewer's question for potential feedback
        # if os.getenv("EVAL_MODE") == "true":
        #     score_prompt = self._get_prompt(prompt_type="score_question")
        #     self.add_event(sender=self.name,
        #                tag="score_question_prompt", content=score_prompt)

        #     score_response = await self.call_engine_async(score_prompt)
        #     self.add_event(sender=self.name,
        #                  tag="score_question_response", content=score_response)

        #     # Extract the score and reasoning
        #     self.question_score, self.question_score_reasoning = \
        #         self._extract_response(score_response)

        prompt = self._get_prompt(prompt_type="respond_to_question")
        self.add_event(sender=self.name,
                       tag="respond_to_question_prompt", content=prompt)

        response = await self.call_engine_async(prompt)
        self.add_event(sender=self.name,
                       tag="respond_to_question_response", content=response)
        self.add_event(sender=self.name,
                       tag="message", content=response)

        # Wait to mimic natural response time
        await asyncio.sleep(3)

        self.interview_session.add_message_to_chat_history(
            role=self.title, content=response, message_type=MessageType.CONVERSATION)

        # # Extract the response content and reasoning
        # response_content, response_reasoning = self._extract_response(response)
        # wants_to_respond = response_content != "SKIP"

        # if wants_to_respond:
        #     # Generate detailed response using LLM

        #     # Extract just the <response> content to send to chat history
        #     self.add_event(sender=self.name, tag="message",
        #                    content=response_content)
        #     self.interview_session.add_message_to_chat_history(
        #         role=self.title, content=response_reasoning, 
        #             message_type=MessageType.FEEDBACK)
        #     self.interview_session.add_message_to_chat_history(
        #         role=self.title, content=response_content, 
        #             message_type=MessageType.CONVERSATION)

        # else:
        #     # We SKIP the response and log a feedback message
        #     self.interview_session.add_message_to_chat_history(
        #         role=self.title, content=response_reasoning, 
        #             message_type=MessageType.FEEDBACK)
        #     self.interview_session.add_message_to_chat_history(
        #         role=self.title, message_type=MessageType.SKIP)

    def _get_prompt(self, prompt_type: str) -> str:
        """Get the formatted prompt for the LLM"""
        from agents.user.prompts import get_prompt

        if prompt_type == "score_question":
            return get_prompt(prompt_type).format(
                profile_background=self.profile_background,
                conversational_style=self.conversational_style,
                session_history=self.session_history,
                current_topic_title=self.current_topic["title"],
                current_topic_description=self.current_topic["description"],
                chat_history=self.get_event_stream_str([{"tag": "message"}])
            )
        elif prompt_type == "respond_to_question":
            return get_prompt(prompt_type).format(
                profile_background=self.profile_background,
                conversational_style=self.conversational_style,
                session_history=self.session_history,
                current_topic_title=self.current_topic["title"],
                current_topic_description=self.current_topic["description"],
                # score=self.question_score,
                # score_reasoning=self.question_score_reasoning,
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
