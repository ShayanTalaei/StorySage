import asyncio
import time
from typing import Dict, Type, Optional, Any, Callable
from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, SkipValidation

from utils.speech.text_to_speech import TextToSpeechBase, create_tts_engine
from utils.speech.audio_player import create_audio_player, AudioPlayerBase
from utils.constants.colors import RED, RESET, GREEN


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