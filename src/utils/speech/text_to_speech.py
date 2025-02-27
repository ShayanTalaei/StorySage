from abc import ABC, abstractmethod
from typing import Optional
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class TextToSpeechBase(ABC):
    """Base class for text-to-speech implementations"""
    
    @abstractmethod
    def text_to_speech(self, text: str, output_path: Optional[str] = None) -> str:
        """Convert text to speech and save to file"""
        pass

class OpenAITTS(TextToSpeechBase):
    """OpenAI's text-to-speech implementation using Whisper"""
    
    def __init__(self, voice: str = "alloy"):
        """
        Initialize OpenAI TTS
        
        Args:
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
        """
        self.client = OpenAI()
        self.voice = voice
        
    def text_to_speech(self, text: str, output_path: Optional[str] = None) -> str:
        """
        Convert text to speech using OpenAI's API
        
        Args:
            text: Text to convert to speech
            output_path: Path to save audio file. If None, will generate one
            
        Returns:
            Path to the saved audio file
        """
        if output_path is None:
            output_path = f"{os.getenv('DATA_DIR', 'data')}/temp_audio_{hash(text)}.mp3"
            
        response = self.client.audio.speech.create(
            model="tts-1",
            voice=self.voice,
            input=text
        )
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        # Write the binary content directly to file
        with open(output_path, 'wb') as f:
            f.write(response.content)
            
        return output_path

class GoogleTTS(TextToSpeechBase):
    """Placeholder for Google TTS implementation"""
    def text_to_speech(self, text: str, output_path: Optional[str] = None) -> str:
        raise NotImplementedError("Google TTS not implemented yet")

def create_tts_engine(provider: str = "openai", **kwargs) -> TextToSpeechBase:
    """Factory function to create TTS engine"""
    providers = {
        "openai": OpenAITTS,
        "google": GoogleTTS
    }
    
    if provider not in providers:
        raise ValueError(f"Unknown provider: {provider}. Available providers: {list(providers.keys())}")
        
    return providers[provider](**kwargs) 