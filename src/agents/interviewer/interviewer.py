import os
import re
from typing import TYPE_CHECKING, TypedDict
from dotenv import load_dotenv


from agents.base_agent import BaseAgent
from agents.interviewer.prompts import CONVERSATION_STARTER, get_prompt
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
                    f"{os.getenv('DATA_DIR', 'data')}/{config.get('user_id')}/",
                on_response=self._handle_response,
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

    def _handle_response(self, response: str) -> None:
        """Handle responses from the RespondToUser tool by adding them to chat history.
        
        Args:
            response: The response text to add to chat history
        """
        self.interview_session.add_message_to_chat_history(
            role=self.title,
            content=response
        )
        self.add_event(sender=self.name, tag="message",
                       content=response)

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
            self.add_event(sender=self.name, tag="llm_prompt", content=prompt)
            response = await self.call_engine_async(prompt)
            print(f"{GREEN}Interviewer:\n{response}{RESET}")
   
            try:
                await self.handle_tool_calls_async(response)
            except Exception as e:
                print(f"Error calling tool: {e}. Use the raw response as the output.")
                self._handle_response(response)

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
        prompt_type = "baseline" if self.use_baseline else "normal"
        main_prompt = get_prompt(prompt_type)

        # Get user portrait and last meeting summary from session note
        user_portrait_str = self.interview_session.session_note \
            .get_user_portrait_str()
        last_meeting_summary_str = (
            self.interview_session.session_note
            .get_last_meeting_summary_str()
        )

        # Get chat history from event stream where these are the senders
        chat_history_events = self.get_event_stream_str(
            [
                {"sender": "Interviewer", "tag": "message"},
                {"sender": "User", "tag": "message"},
                {"sender": "system", "tag": "recall"},
            ],
            as_list=True
        )
        
        recent_events = chat_history_events[-self._max_events_len:] if \
            len(chat_history_events) > self._max_events_len else chat_history_events
        current_events = recent_events[-2:] if len(recent_events) >= 2 else recent_events

        all_interviewer_messages = self.get_event_stream_str(
            [{"sender": "Interviewer", "tag": "message"}],
            as_list=True
        )
        recent_interviewer_messages = all_interviewer_messages[-5:] if \
            len(all_interviewer_messages) >= 5 else all_interviewer_messages

        # Start with all available tools
        tools_set = set(self.tools.keys())
        
        # if self.interview_session.api_participant:
        #     # Don't end_conversation directly if API participant is present
        #     tools_set.discard("end_conversation")
        
        if self.use_baseline:
            # For baseline mode, remove recall tool
            tools_set.discard("recall")

        # Create format parameters based on prompt type
        format_params = {
            "user_portrait": user_portrait_str,
            "last_meeting_summary": last_meeting_summary_str,
            "chat_history": '\n'.join(recent_events),
            "current_events": '\n'.join(current_events),
            "recent_interviewer_messages": '\n'.join(
                [ msg[:120] + "..." if len(msg) > 150 else msg \
                    for msg in recent_interviewer_messages]),
            "conversation_starter": CONVERSATION_STARTER \
                if len(all_interviewer_messages) == 0 and \
                int(self.interview_session.session_id) != 1 \
                else "",
            "tool_descriptions": self.get_tools_description(list(tools_set))
        }
        
        # Only add questions_and_notes for normal mode
        if not self.use_baseline:
            questions_and_notes_str = self.interview_session.session_note \
                .get_questions_and_notes_str(
                    hide_answered="qa"
                )
            format_params["questions_and_notes"] = questions_and_notes_str

        return format_prompt(main_prompt, format_params)
