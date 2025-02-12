import asyncio
import time
from typing import Dict, Type, Optional, Any, Callable
from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException
from pydantic import BaseModel, Field, SkipValidation

from content.memory_bank.memory_bank_base import MemoryBankBase
from utils.text_to_speech import TextToSpeechBase, create_tts_engine
from utils.audio_player import create_audio_player, AudioPlayerBase
from utils.colors import RED, RESET, GREEN


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
    memory_bank: MemoryBankBase = Field(...)
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
    description: str = "A tool for responding to the user."
    args_schema: Type[BaseModel] = ResponseToUserInput
    
    tts_config: Dict = Field(default_factory=dict)
    base_path: str = Field(...)
    on_response: SkipValidation[Callable[[str], None]] = Field(
        description="Callback function to be called when responding to user"
    )
    on_turn_complete: SkipValidation[Callable[[], None]] = Field(
        description="Callback function to be called when turn is complete"
    )
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
        self.on_response(response)
        
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
        
        self.on_turn_complete()
            
        return "Response sent to the user."

class EndConversationInput(BaseModel):
    goodbye: str = Field(description="The goodbye message to the user. Tell the user that you are looking forward to talking to them in the next session.")

class EndConversation(BaseTool):
    """Tool for ending the conversation."""
    name: str = "end_conversation"
    description: str = "A tool for ending the conversation."
    args_schema: Type[BaseModel] = EndConversationInput
    
    on_goodbye: SkipValidation[Callable[[str], None]] = Field(
        description="Callback function to be called with goodbye message"
    )
    on_end: SkipValidation[Callable[[], None]] = Field(
        description="Callback function to be called when conversation ends"
    )

    def _run(
        self,
        goodbye: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Any:
        self.on_goodbye(goodbye)
        
        time.sleep(1)
        
        # Call the end callback if provided
        self.on_end()
            
        return "Conversation ended successfully."