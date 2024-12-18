import argparse
import os
from dotenv import load_dotenv
import asyncio
import contextlib
import uvicorn

from interview_session.interview_session import InterviewSession
from database.setup_db import setup_database

load_dotenv(override=True)

async def run_terminal_mode(args):
    if args.restart:
        os.system(f"rm -rf {os.getenv('LOGS_DIR')}/{args.user_id}")
        os.system(f"rm -rf {os.getenv('DATA_DIR')}/{args.user_id}")
    
    interview_session = InterviewSession(args.user_id, 'agent' if args.user_agent else 'terminal', args.voice_output, args.voice_input)
    with contextlib.suppress(KeyboardInterrupt):
        await interview_session.run()

def run_server_mode(port: int):
    import api.app
    uvicorn.run(api.app.app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run interviewer with specific user and session')

    # Three modes: terminal, server, and setup_db
    parser.add_argument('--mode', choices=['terminal', 'server', 'setup_db'], default='terminal', help='Run mode: terminal, server, or setup_db')

    # Server mode arguments
    parser.add_argument('--port', type=int, default=8000, help='Port number for server mode')
    
    # Terminal mode arguments
    parser.add_argument('--user_id', help='User ID for the session')
    parser.add_argument('--user_agent', action='store_true', default=False, help='Use user agent')
    parser.add_argument('--voice_output', action='store_true', default=False, help='Enable voice output')
    parser.add_argument('--voice_input', action='store_true', default=False, help='Enable voice input')
    parser.add_argument('--restart', action='store_true', default=False, help='Restart the session')
    
    # Setup_db mode arguments
    parser.add_argument('--reset', action='store_true', help='Reset database (clear all data)')
    
    args = parser.parse_args()
    
    # Run the appropriate mode
    if args.mode == 'terminal':
        if not args.user_id:
            parser.error("--user_id is required for terminal mode")
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(run_terminal_mode(args))
    elif args.mode == 'server':
        run_server_mode(args.port)
    elif args.mode == 'setup_db':
        setup_database(reset=args.reset)
    else:
        parser.error(f"Invalid mode: {args.mode}")
    
