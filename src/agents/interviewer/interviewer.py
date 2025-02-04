import asyncio
import os
import time
from typing import Dict, Type, Optional, Any, TYPE_CHECKING, TypedDict
from dotenv import load_dotenv
from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException
from pydantic import BaseModel, Field
from datetime import datetime
from agents.base_agent import BaseAgent
from agents.interviewer.prompts import get_prompt
from agents.prompt_utils import format_prompt
from memory_bank.memory_bank_vector_db import MemoryBank
from interview_session.session_models import Participant, Message
from utils.text_to_speech import TextToSpeechBase, create_tts_engine
from utils.audio_player import create_audio_player, AudioPlayerBase

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession

load_dotenv()

# Console colors
GREEN = '\033[92m'
ORANGE = '\033[93m'
RESET = '\033[0m'
RED = '\033[91m'

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
        Participant.__init__(self, title="Interviewer", interview_session=interview_session)
        
        self.user_id = config.get("user_id")
        self.max_events_len = int(os.getenv("MAX_EVENTS_LEN", 40))
        self.max_consideration_iterations = int(os.getenv("MAX_CONSIDERATION_ITERATIONS", 3))
        
        # Initialize TTS configuration
        tts_config = config.get("tts", {})
        self.base_path = f"data/{self.user_id}/"
        
        # Initialize tools
        self.tools = {
            "recall": Recall(memory_bank=self.interview_session.memory_bank),
            "respond_to_user": RespondToUser(
                interviewer=self,
                tts_config=tts_config,
                base_path=self.base_path
            ),
            "end_conversation": EndConversation(interviewer=self)
        }
        
        self.turn_to_respond = False

    async def on_message(self, message: Message):
        
        if message:
            print(f"{datetime.now()} ✅ Interviewer received message from {message.role}")
            self.add_event(sender=message.role, tag="message", content=message.content)

        # This boolean is set to False when the interviewer is done responding (it has used respond_to_user tool)
        self.turn_to_respond = True
        iterations = 0

        while self.turn_to_respond and iterations < self.max_consideration_iterations:
            # Get updated prompt with current chat history, session note, etc. This may change periodically (e.g. when the interviewer receives a system message that triggers a recall)
            prompt = self.get_prompt()
            # Logs the prompt to the event stream
            self.add_event(sender=self.name, tag="prompt", content=prompt)
            # Call the LLM engine with the updated prompt, This is the prompt the interviewer gives to the LLM to formulate it's response (includes thinking and tool calls)
            response = await self.call_engine_async(prompt)
            # Prints the green text in the console
            print(f"{GREEN}Interviewer:\n{response}{RESET}")
            # Logs the interviewer's (LLM) response to the event stream
            self.add_event(sender=self.name, tag="interviewer_response", content=response)
            # Handle tool calls in the response
            await self.handle_tool_calls_async(response)
            
            # Increment iteration count
            iterations += 1

            if iterations >= self.max_consideration_iterations:
                self.add_event(
                    sender="system",
                    tag="error",
                    content=f"Exceeded maximum number of consideration iterations ({self.max_consideration_iterations})"
                )

    def get_prompt(self):
        '''Gets the prompt for the interviewer. The logic for this is in the get_prompt function in interviewer/prompts.py'''
        main_prompt = get_prompt()
        # Get user portrait and last meeting summary from session note
        user_portrait_str = self.interview_session.session_note.get_user_portrait_str()
        last_meeting_summary_str = self.interview_session.session_note.get_last_meeting_summary_str()
        # Get chat history from event stream where these are the senders
        # Upon using a tool, the tool name is added to the event stream with the tag as the tool name
        # This is important for letting the agent know the system response if a tool is called.
        chat_history_str = self.get_event_stream_str(
            [
                {"sender": "Interviewer", "tag": "interviewer_response"},
                {"sender": "User", "tag": "message"},
                {"sender": "system", "tag": "recall"},
            ],
            as_list=True
        )
        questions_and_notes_str = self.interview_session.session_note.get_questions_and_notes_str(hide_answered="qa")
        ## TODO: Add additional notes
        tool_descriptions_str = self.get_tools_description()
        recent_events = chat_history_str[-self.max_events_len:] if len(chat_history_str) > self.max_events_len else chat_history_str
        
        return format_prompt(main_prompt, {
            "user_portrait": user_portrait_str,
            "last_meeting_summary": last_meeting_summary_str,
            "chat_history": '\n'.join(recent_events),
            "questions_and_notes": questions_and_notes_str,
            "tool_descriptions": tool_descriptions_str
        })
        
class RecallInput(BaseModel):
    reasoning: str = Field(description="Explain how this information will help you answer the user's question.")
    query: str = Field(description=("The query to search for in the memory bank. "
                                   "This should be a short phrase or sentence that captures the essence of the information you want to recall." 
                                   "For example, you can ask about a specific event, a person, a feeling, etc. "
                                   "You can also query more specifically, like 'a daytrip to the zoo'."))

class Recall(BaseTool):
    """Tool for recalling memories."""

    name: str = "recall"
    description: str = (
        "A tool for recalling memories. "
        "Whenever you need to recall information about the user, you can use call this tool."
    )
    args_schema: Type[BaseModel] = RecallInput
    memory_bank: MemoryBank = Field(...)
    handle_tool_error: bool = True
    correct_directory_path: str = ""

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Any:
        """Use the tool to run the Python code."""

        try:
            memories = self.memory_bank.search_memories(query)
            memories_str = "\n".join([f"Memory {i+1}:\n{memory['text']}" for i, memory in enumerate(memories)])
            return memories_str
        except Exception as e:  
            raise ToolException(f"Error recalling memories: {e}")

class ResponseToUserInput(BaseModel):
    response: str = Field(description="The response to the user.")

class RespondToUser(BaseTool):
    """Tool for responding to the user."""

    name: str = "respond_to_user"
    description: str = (
        "A tool for responding to the user."
    )
    interviewer: Interviewer = Field(...)
    tts_config: Dict = Field(default_factory=dict)
    base_path: str = Field(...)
    args_schema: Type[BaseModel] = ResponseToUserInput
    tts_engine: Optional[Any] = Field(default=None, exclude=True)
    audio_player: Optional[Any] = Field(default=None, exclude=True)

    def __init__(self, **data):
        super().__init__(**data)
        if self.tts_config.get("enabled", False):
            self.tts_engine: TextToSpeechBase = create_tts_engine(
                provider=self.tts_config.get("provider", "openai"),
                voice=self.tts_config.get("voice", "alloy")
            )
            self.audio_player: AudioPlayerBase = create_audio_player()

    async def _run(
        self,
        response: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Any:
        interview_session = self.interviewer.interview_session
        interview_session.add_message_to_chat_history(role=self.interviewer.title, content=response)
        
        if self.tts_engine:
            try:
                audio_path = await asyncio.to_thread(
                    self.tts_engine.text_to_speech,
                    response,
                    f"{self.base_path}/audio_outputs/response_{int(time.time())}.mp3"
                )
                print(f"{GREEN}Audio saved to: {audio_path}{RESET}")
                
                await asyncio.to_thread(self.audio_player.play, audio_path)
                
            except Exception as e:
                print(f"{RED}Failed to generate/play speech: {e}{RESET}")
        
        self.interviewer.turn_to_respond = False
        return "Response sent to the user."

class EndConversationInput(BaseModel):
    goodbye: str = Field(description="The goodbye message to the user. Tell the user that you are looking forward to talking to them in the next session.")

class EndConversation(BaseTool):
    """Tool for ending the conversation."""

    name: str = "end_conversation"
    description: str = (
        "A tool for ending the conversation."
    )
    args_schema: Type[BaseModel] = EndConversationInput
    interviewer: Interviewer = Field(...)

    def _run(
        self,
        goodbye: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Any:
        interview_session = self.interviewer.interview_session
        # Add the goodbye message to both chat histories
        self.interviewer.add_event(sender=self.interviewer.name, tag="goodbye", content=goodbye)
        interview_session.add_message_to_chat_history(role=self.interviewer.title, content=goodbye)
        
        # Sets boolean to False so loop in handle_tool_calls will break
        self.interviewer.turn_to_respond = False
        time.sleep(1)
        interview_session.end_session()
        return "Conversation ended successfully."