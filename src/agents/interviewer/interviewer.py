import os
import re
from typing import TYPE_CHECKING, TypedDict
from dotenv import load_dotenv


from agents.base_agent import BaseAgent
from agents.interviewer.prompts import get_prompt
from agents.interviewer.tools import EndConversation, RespondToUser
from agents.note_taker.tools import Recall
from utils.llm.prompt_utils import format_prompt
from interview_session.session_models import Participant, Message
from utils.logger import SessionLogger
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
        BaseAgent.__init__(self, name="Interviewer",
                           description="The agent that interviews the user, asking questions about the user's life.",
                           config=config)
        Participant.__init__(self, title="Interviewer",
                             interview_session=interview_session)

        self._max_events_len = int(os.getenv("MAX_EVENTS_LEN", 30))
        self._max_consideration_iterations = int(
            os.getenv("MAX_CONSIDERATION_ITERATIONS", 3))

        # Initialize tools
        self.tools = {
            "recall": Recall(memory_bank=self.interview_session.memory_bank),
            "respond_to_user": RespondToUser(
                tts_config=config.get("tts", {}),
                base_path=f"{os.getenv('DATA_DIR', 'data')}/{config.get("user_id")}/",
                on_response=lambda response: self.interview_session.add_message_to_chat_history(
                    role=self.title,
                    content=response
                ),
                on_turn_complete=lambda: setattr(
                    self, 'turn_to_respond', False)
            ),
            "end_conversation": EndConversation(
                on_goodbye=lambda goodbye: (
                    self.add_event(sender=self.name,
                                   tag="goodbye", content=goodbye),
                    self.interview_session.add_message_to_chat_history(
                        role=self.title, content=goodbye)
                ),
                on_end=lambda: (
                    setattr(self, 'turn_to_respond', False),
                    self.interview_session.end_session()
                )
            )
        }

        self.turn_to_respond = False

    async def on_message(self, message: Message):

        if message:
            SessionLogger.log_to_file(
                "execution_log", f"[NOTIFY] Interviewer received message from {message.role}")
            self.add_event(sender=message.role, tag="message",
                           content=message.content)
        
        if not self.interview_session.session_in_progress:
            return
        
        # This boolean is set to False when the interviewer is done responding (it has used respond_to_user tool)
        self.turn_to_respond = True
        iterations = 0

        while self.turn_to_respond and iterations < self._max_consideration_iterations:
            # Get updated prompt with current chat history, session note, etc. This may change periodically (e.g. when the interviewer receives a system message that triggers a recall)
            prompt = self.get_prompt()
            # Logs the prompt to the event stream
            self.add_event(sender=self.name, tag="prompt", content=prompt)
            # Call the LLM engine with the updated prompt, This is the prompt the interviewer gives to the LLM to formulate it's response (includes thinking and tool calls)
            response = await self.call_engine_async(prompt)
            # Prints the green text in the console
            print(f"{GREEN}Interviewer:\n{response}{RESET}")

            response_content, question_id, thinking = self._extract_response(
                response)

            # Format the response with question ID if available
            formatted_response = f"Question {question_id}:\n\n{response_content}" if question_id else response_content

            self.add_event(sender=self.name, tag="message",
                           content=formatted_response)
            # Handle tool calls in the response
            await self.handle_tool_calls_async(response)

            # Increment iteration count
            iterations += 1

            if iterations >= self._max_consideration_iterations:
                self.add_event(
                    sender="system",
                    tag="error",
                    content=f"Exceeded maximum number of consideration iterations ({self._max_consideration_iterations})"
                )

    def get_prompt(self):
        '''
        Gets the prompt for the interviewer. 
        The logic for this is in the get_prompt function in interviewer/prompts.py
        '''
        main_prompt = get_prompt()
        # Get user portrait and last meeting summary from session note
        user_portrait_str = self.interview_session.session_note.get_user_portrait_str()
        last_meeting_summary_str = self.interview_session.session_note.get_last_meeting_summary_str()
        # Get chat history from event stream where these are the senders
        # Upon using a tool, the tool name is added to the event stream with the tag as the tool name
        # This is important for letting the agent know the system response if a tool is called.
        chat_history_str = self.get_event_stream_str(
            [
                {"sender": "Interviewer", "tag": "message"},
                {"sender": "User", "tag": "message"},
                {"sender": "system", "tag": "recall"},
            ],
            as_list=True
        )
        questions_and_notes_str = self.interview_session.session_note.get_questions_and_notes_str(
            hide_answered="qa")
        # TODO: Add additional notes
        tool_descriptions_str = self.get_tools_description()
        recent_events = chat_history_str[-self._max_events_len:] if len(
            chat_history_str) > self._max_events_len else chat_history_str

        return format_prompt(main_prompt, {
            "user_portrait": user_portrait_str,
            "last_meeting_summary": last_meeting_summary_str,
            "chat_history": '\n'.join(recent_events),
            "questions_and_notes": questions_and_notes_str,
            "tool_descriptions": tool_descriptions_str
        })

    def _extract_response(self, full_response: str) -> tuple[str, str]:
        """Extract the content between <response_content> and <thinking> tags"""
        response_match = re.search(
            r'<response>(.*?)</response>', full_response, re.DOTALL)
        thinking_match = re.search(
            r'<thinking>(.*?)</thinking>', full_response, re.DOTALL)

        question_id_match = re.search(
            r'<current_question_id>(.*?)</current_question_id>', full_response, re.DOTALL)
        question_id = question_id_match.group(
            1).strip() if question_id_match else None
        response = response_match.group(
            1).strip() if response_match else full_response
        thinking = thinking_match.group(1).strip() if thinking_match else ""

        return response, question_id, thinking
