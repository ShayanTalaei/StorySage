import time
from typing import Dict, Type, Optional, Any, TYPE_CHECKING

from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException
from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from agents.interviewer.prompts import get_prompt
from agents.prompt_utils import format_prompt
from memory_bank.memory_bank_vector_db import MemoryBank
from interview_session.session_models import Participant, Message
from utils.text_to_speech import create_tts_engine
from utils.audio_player import create_audio_player, AudioPlayerBase

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession

# Console colors
GREEN = '\033[92m'
ORANGE = '\033[93m'
RESET = '\033[0m'
RED = '\033[91m'

class Interviewer(BaseAgent, Participant):
    def __init__(self, config: Dict, interview_session: 'InterviewSession'):
        BaseAgent.__init__(self, name="Interviewer", 
                         description="The agent that interviews the user, asking questions about the user's life.",
                         config=config)
        Participant.__init__(self, title="Interviewer", interview_session=interview_session)
        
        self.user_id = config.get("user_id")
        self.memory_bank = MemoryBank.load_from_file(self.user_id)
        
        # Initialize TTS configuration
        tts_config = config.get("tts", {})
        self.base_path = f"data/{self.user_id}/"
        
        self.tools = {
            "recall": Recall(memory_bank=self.memory_bank),
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
            self.add_event(sender=message.role, tag="message", content=message.content)
        self.turn_to_respond = True
        while self.turn_to_respond:
            prompt = self.get_prompt()
            self.add_event(sender=self.name, tag="prompt", content=prompt)
            response = self.call_engine(prompt)
            self.add_event(sender=self.name, tag="llm_response", content=response)
            print(f"{GREEN}Interviewer:\n{response}{RESET}")
        
            # Add interviewer's response to both chat histories
            self.add_event(sender=self.name, tag="interviewer_response", content=response)
            
            self.handle_tool_calls(response)
    
    def get_prompt(self):
        main_prompt = get_prompt()
        
        user_portrait_str = self.interview_session.session_note.get_user_portrait_str()
        last_meeting_summary_str = self.interview_session.session_note.get_last_meeting_summary_str()
        chat_history_str = self.get_event_stream_str()
        questions_and_notes_str = self.interview_session.session_note.get_questions_and_notes_str(hide_answered="qa")
        ## TODO: Add additional notes
        tool_descriptions_str = self.get_tools_description()
        
        return format_prompt(main_prompt, {
            "user_portrait": user_portrait_str,
            "last_meeting_summary": last_meeting_summary_str,
            "chat_history": chat_history_str,
            "questions_and_notes": questions_and_notes_str,
            "tool_descriptions": tool_descriptions_str
        })
        
class RecallInput(BaseModel):
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
            self.tts_engine = create_tts_engine(
                provider=self.tts_config.get("provider", "openai"),
                voice=self.tts_config.get("voice", "alloy")
            )
            self.audio_player: AudioPlayerBase = create_audio_player()

    def _run(
        self,
        response: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Any:
        interview_session = self.interviewer.interview_session
        interview_session.add_message_to_chat_history(role=self.interviewer.title, content=response)
        
        # Generate speech if TTS is enabled
        if self.tts_engine:
            try:
                audio_path = self.tts_engine.text_to_speech(
                    response,
                    output_path=f"{self.base_path}/audio_outputs/response_{int(time.time())}.mp3"
                )
                print(f"{GREEN}Audio saved to: {audio_path}{RESET}")
                
                # Play the audio
                self.audio_player.play(audio_path)
                
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
        
        self.interviewer.turn_to_respond = False
        time.sleep(1)
        interview_session.session_in_progress = False
        return "Conversation ended successfully."