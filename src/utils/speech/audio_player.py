from abc import ABC, abstractmethod
import platform
import subprocess
import os

class AudioPlayerBase(ABC):
    """Base class for audio playback implementations"""
    
    @abstractmethod
    def play(self, audio_path: str):
        """Play audio file"""
        pass

class SystemAudioPlayer(AudioPlayerBase):
    """Uses system commands to play audio"""
    
    def play(self, audio_path: str):
        system = platform.system()
        
        try:
            if system == 'Darwin':  # macOS
                subprocess.run(['afplay', audio_path], check=True)
            elif system == 'Linux':
                subprocess.run(['play', audio_path], check=True)  # Requires sox
            elif system == 'Windows':
                os.startfile(audio_path)  # Uses default media player
            else:
                raise NotImplementedError(f"Unsupported platform: {system}")
        except subprocess.CalledProcessError as e:
            print(f"Error playing audio: {e}")
        except FileNotFoundError:
            if system == 'Linux':
                print("Please install 'sox' to play audio (sudo apt-get install sox)")
            else:
                print(f"Could not find audio player for {system}")

def create_audio_player() -> AudioPlayerBase:
    """Factory function to create audio player"""
    return SystemAudioPlayer() 