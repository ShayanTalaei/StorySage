import argparse
import os
from dotenv import load_dotenv
import asyncio
import contextlib

from interview_session.interview_session import InterviewSession

load_dotenv(override=True)

async def main(args):
    if args.restart:
        # delete user's directory
        os.system(f"rm -rf {os.getenv('LOGS_DIR')}/{args.user_id}")
        os.system(f"rm -rf {os.getenv('DATA_DIR')}/{args.user_id}")
    
    interview_session = InterviewSession(args.user_id, args.user_agent, args.voice_output, args.voice_input)
    with contextlib.suppress(KeyboardInterrupt):
        await interview_session.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run interviewer with specific user and session')
    parser.add_argument('--user_id', required=True, help='User ID for the session')
    parser.add_argument('--user_agent', action='store_true', default=False, help='Use user agent')
    parser.add_argument('--voice_output', action='store_true', default=False, help='Enable voice output')
    parser.add_argument('--voice_input', action='store_true', default=False, help='Enable voice input')
    parser.add_argument('--restart', action='store_true', default=False, help='Restart the session')
    
    args = parser.parse_args()
    
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main(args))
    
    