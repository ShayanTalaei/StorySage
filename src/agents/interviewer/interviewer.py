import os
import re
from typing import TYPE_CHECKING, TypedDict
from dotenv import load_dotenv


from agents.base_agent import BaseAgent
from agents.interviewer.prompts import get_prompt
from agents.interviewer.tools import EndConversation, RespondToUser
from agents.shared.memory_tools import Recall
from utils.llm.prompt_utils import format_prompt
from interview_session.session_models import Participant, Message
from utils.logger.session_logger import SessionLogger
from utils.constants.colors import GREEN, RESET

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession

load_dotenv()


class TTSConfig(TypedDict, total=False):
    """Configuration for text-to-speech."""
    enabled: bool
    provider: str  # e.g. 'openai'
    voice: str     # e.g. 'alloy'


class InterviewerConfig(TypedDict, total=False):
    """Configuration for the Interviewer agent."""
    user_id: str
    tts: TTSConfig


class Interviewer(BaseAgent, Participant):
    '''Inherits from BaseAgent and Participant. Participant is a class that all agents in the interview session inherit from.'''

    def __init__(self, config: InterviewerConfig, interview_session: 'InterviewSession'):
        BaseAgent.__init__(
            self, name="Interviewer",
            description="The agent that holds the interview and asks questions.",
            config=config)
        Participant.__init__(
            self, title="Interviewer",
            interview_session=interview_session)

        self.tools = {
            "recall": Recall(memory_bank=self.interview_session.memory_bank),
            "respond_to_user": RespondToUser(
                tts_config=config.get("tts", {}),
                base_path= \
                    f"{os.getenv('DATA_DIR', 'data')}/{config.get("user_id")}/",
                on_response=lambda response: \
                    self.interview_session.add_message_to_chat_history(
                        role=self.title,
                        content=response
                    ),
                on_turn_complete=lambda: setattr(
                    self, '_turn_to_respond', False)
            ),
            # "end_conversation": EndConversation(
            #     on_goodbye=lambda goodbye: (
            #         self.add_event(sender=self.name,
            #                        tag="goodbye", content=goodbye),
            #         self.interview_session.add_message_to_chat_history(
            #             role=self.title, content=goodbye)
            #     ),
            #     on_end=lambda: (
            #         setattr(self, '_turn_to_respond', False),
            #         self.interview_session.end_session()
            #     )
            # )
        }

        self._turn_to_respond = False

    async def on_message(self, message: Message):

        if message:
            SessionLogger.log_to_file(
                "execution_log",
                f"[NOTIFY] Interviewer received message from {message.role}"
            )
            self.add_event(sender=message.role, tag="message",
                           content=message.content)
        
        self._turn_to_respond = True
        iterations = 0

        while self._turn_to_respond and iterations < self._max_consideration_iterations:
            prompt = self._get_prompt()
            self.add_event(sender=self.name, tag="prompt", content=prompt)
            response = await self.call_engine_async(prompt)
            print(f"{GREEN}Interviewer:\n{response}{RESET}")

            response_content = self._extract_response(response)

            self.add_event(sender=self.name, tag="message",
                           content=response_content)
            
            await self.handle_tool_calls_async(response)

            iterations += 1
            if iterations >= self._max_consideration_iterations:
                self.add_event(
                    sender="system",
                    tag="error",
                    content=f"Exceeded maximum number of consideration "
                    f"iterations ({self._max_consideration_iterations})"
                )

    def _get_prompt(self):
        '''Gets the prompt for the interviewer. '''
        # Use the baseline prompt if enabled
        prompt_type = "baseline" if self._use_baseline else "normal"

        main_prompt = get_prompt(prompt_type)
        # Get user portrait and last meeting summary from session note
        user_portrait_str = self.interview_session.session_note \
            .get_user_portrait_str()
        last_meeting_summary_str = (
            self.interview_session.session_note
            .get_last_meeting_summary_str()
        )
        # Get chat history from event stream where these are the senders
        chat_history_str = self.get_event_stream_str(
            [
                {"sender": "Interviewer", "tag": "message"},
                {"sender": "User", "tag": "message"},
                {"sender": "system", "tag": "recall"},
            ],
            as_list=True
        )

        # Start with all available tools
        tools_set = set(self.tools.keys())
        
        # if self.interview_session.api_participant:
        #     # Don't end_conversation directly if API participant is present
        #     tools_set.discard("end_conversation")
        
        if self._use_baseline:
            # For baseline mode, remove recall tool
            tools_set.discard("recall")
        
        # Get tool descriptions for the filtered tools
        tool_descriptions_str = self.get_tools_description(list(tools_set))
        
        recent_events = chat_history_str[-self._max_events_len:] if \
            len(chat_history_str) > self._max_events_len else chat_history_str

        # Create format parameters based on prompt type
        format_params = {
            "user_portrait": user_portrait_str,
            "last_meeting_summary": last_meeting_summary_str,
            "chat_history": '\n'.join(recent_events),
            "user_message": recent_events[-1] if recent_events else "",
            "tool_descriptions": tool_descriptions_str
        }
        
        # Only add questions_and_notes for normal mode
        if not self._use_baseline:
            questions_and_notes_str = self.interview_session.session_note \
                .get_questions_and_notes_str(
                    hide_answered="qa"
                )
            format_params["questions_and_notes"] = questions_and_notes_str

        return format_prompt(main_prompt, format_params)

    def _extract_response(self, full_response: str) -> str:
        """Extract the content between <response_content> and <thinking> tags"""
        response_match = re.search(
            r'<response>(.*?)</response>', full_response, re.DOTALL)
        response = response_match.group(
            1).strip() if response_match else full_response
        return response
