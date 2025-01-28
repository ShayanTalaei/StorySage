import os
import sys
from pathlib import Path

# Add the src directory to Python path
src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from session_note.session_note import SessionNote

def visualize_session_note(file_path: str):
    """Load and visualize topics from a session note file."""
    try:
        # Load the session note
        session_note = SessionNote.load_from_file(file_path)
        
        # Print basic session info
        print(f"\nSession {session_note.session_id} - {session_note.user_id}")
        print("=" * 50)
        
        # Visualize the topics
        print(session_note.visualize_topics())
        
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    for i in range(0, 6):
        default_file = f"logs/maggie/session_notes/session_{i}.json"
        print(f"Visualizing session {i}")
        visualize_session_note(default_file)
        print("\n" + "=" * 50 + "\n")
