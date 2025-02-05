import os
import sys
import argparse
from pathlib import Path

# Add the src directory to Python path
src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from session_note.session_note import SessionNote

def get_session_ids(user_id: str) -> list[int]:
    """
    Get all available session IDs for a given user.
    
    Args:
        user_id (str): The user ID to check
        
    Returns:
        list[int]: List of available session IDs
    """
    session_dir = Path(os.getenv("LOGS_DIR", "logs")) / user_id / "session_notes"
    if not session_dir.exists():
        return []
    
    # Find all session_{n}.json files and extract the session numbers
    session_files = session_dir.glob("session_*.json")
    session_ids = []
    
    for file in session_files:
        try:
            # Extract number from "session_X.json"
            session_id = int(file.stem.split('_')[1])
            session_ids.append(session_id)
        except (IndexError, ValueError):
            continue
    
    return sorted(session_ids)

def visualize_session_note(user_id: str, session_id: int) -> None:
    """
    Load and visualize topics from a session note file.
    
    Args:
        user_id (str): The user ID (e.g., 'maggie')
        session_id (int): The session number
    """
    file_path = Path(os.getenv("LOGS_DIR", "logs")) / user_id / "session_notes" / f"session_{session_id}.json"
    
    try:
        # Load the session note
        session_note = SessionNote.load_from_file(str(file_path))
        
        # Print basic session info
        print(f"\nSession {session_note.session_id} - {session_note.user_id}")
        print("=" * 50)
        
        # Visualize the topics
        print(session_note.visualize_topics())
        
    except FileNotFoundError:
        print(f"Error: Session note file not found at {file_path}")
    except Exception as e:
        print(f"Error processing session note: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Visualize topics from session notes")
    parser.add_argument("--user", "-u", type=str, default="maggie",
                       help="User ID (default: maggie)")
    parser.add_argument("--session", "-s", type=int,
                       help="Specific session ID to visualize")
    parser.add_argument("--latest", "-l", action="store_true",
                       help="Visualize only the latest session")
    
    args = parser.parse_args()
    
    if args.session is not None and args.latest:
        print("Error: Cannot specify both --session and --latest")
        return
        
    # Get all available session IDs
    session_ids = get_session_ids(args.user)
    
    if not session_ids:
        print(f"No session notes found for user '{args.user}'")
        return
        
    print(f"Found {len(session_ids)} sessions for user '{args.user}'")
    
    if args.latest:
        # Visualize only the latest session
        latest_session = max(session_ids)
        print(f"\nVisualizing latest session ({latest_session})")
        visualize_session_note(args.user, latest_session)
    elif args.session is not None:
        # Visualize specific session
        visualize_session_note(args.user, args.session)
    else:
        # Visualize all available sessions
        for session_id in session_ids:
            print(f"\nVisualizing session {session_id}")
            visualize_session_note(args.user, session_id)
            print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
