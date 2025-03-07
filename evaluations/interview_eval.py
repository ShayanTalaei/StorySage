import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime
import asyncio
from typing import Dict, Any, Optional

# Add the src directory to Python path
src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from dotenv import load_dotenv
from utils.llm.engines import get_engine, invoke_engine
from utils.logger.evaluation_logger import EvaluationLogger
from utils.llm.xml_formatter import extract_tool_arguments

load_dotenv()

# Evaluation criteria
EVALUATION_CRITERIA = {
    "smooth_score": {
        "description": "How smooth were the topic transitions in the conversation",
        "scale": "0-5",
        "guidelines": [
            "0: Very abrupt and jarring transitions that felt completely disconnected",
            "1: Mostly abrupt transitions with little connection between topics",
            "2: Some transitions were smooth, but many felt forced or awkward",
            "3: Generally smooth transitions with a few awkward moments",
            "4: Very smooth transitions that felt natural and connected",
            "5: Exceptionally smooth and natural flow between all topics"
        ]
    },
    "flexibility_score": {
        "description": "How flexible was the interview process",
        "scale": "0-5",
        "guidelines": [
            "0: Completely rigid, ignored user responses and followed a strict script",
            "1: Very inflexible, rarely adapted to user responses",
            "2: Somewhat inflexible, occasionally adapted to user responses",
            "3: Moderately flexible, often adapted to user responses",
            "4: Very flexible, consistently adapted to user responses",
            "5: Extremely flexible, fully responsive to user's interests and responses"
        ]
    },
    "quality_score": {
        "description": "Quality of language (grammar, spelling, punctuation, word choice, sentence structure)",
        "scale": "0-5",
        "guidelines": [
            "0: Extremely poor quality with constant errors",
            "1: Poor quality with frequent errors",
            "2: Fair quality with several noticeable errors",
            "3: Good quality with occasional minor errors",
            "4: Very good quality with rare errors",
            "5: Excellent quality with virtually no errors"
        ]
    },
    "comforting_score": {
        "description": "How comfortable the interview experience felt",
        "scale": "0-5",
        "guidelines": [
            "0: Extremely uncomfortable, felt invasive or hostile",
            "1: Very uncomfortable, felt impersonal or mechanical",
            "2: Somewhat uncomfortable at times",
            "3: Generally comfortable with a few awkward moments",
            "4: Very comfortable, felt like talking to a friendly acquaintance",
            "5: Exceptionally comfortable, felt like talking to a trusted friend"
        ]
    }
}

USER_EXPERIENCE_INSTRUCTIONS = """
You are an expert evaluator assessing the quality of an AI interviewer. You will be given a transcript of a conversation between an AI interviewer and a human user. Your task is to evaluate the interview experience from the user's perspective.

Please carefully read through the entire conversation transcript and then provide ratings and explanations for the following criteria:

{criteria_text}

For each criterion, provide:
1. A numerical rating based on the scale
2. A detailed explanation (2-3 sentences) justifying your rating with specific examples from the conversation

Your evaluation should be objective, fair, and based solely on the conversation transcript provided.
"""

USER_EXPERIENCE_IO = """
## Input Context

Conversation Transcript:
<conversation_transcript>
{chat_history}
</conversation_transcript>

## Output Format
Use the tool calls to output your evaluation.

<tool_calls>
<smooth_score>
    <rating>[0-5]</rating>
    <explanation>Your explanation here</explanation>
</smooth_score>
<flexibility_score>
    <rating>[0-5]</rating>
    <explanation>Your explanation here</explanation>
</flexibility_score>
<quality_score>
    <rating>[0-5]</rating>
    <explanation>Your explanation here</explanation>
</quality_score>
<comforting_score>
    <rating>[0-5]</rating>
    <explanation>Your explanation here</explanation>
</comforting_score>
</tool_calls>
"""

def format_evaluation_prompt(chat_history: str) -> str:
    """Format the evaluation prompt with the chat history."""
    
    criteria_text = ""
    for criterion, details in EVALUATION_CRITERIA.items():
        criteria_text += (f"- {criterion.replace('_', ' ').title()}: "
                f"{details['description']}. Rate from {details['scale']}.\n")
        for guideline in details['guidelines']:
            criteria_text += f"  * {guideline}\n"
        criteria_text += "\n"
    
    instructions = USER_EXPERIENCE_INSTRUCTIONS.format(criteria_text=criteria_text)
    io_format = USER_EXPERIENCE_IO.format(chat_history=chat_history)
    
    return f"{instructions}\n\n{io_format}"

def parse_evaluation_response(response: str) -> Dict[str, Any]:
    """Parse the evaluation response to extract ratings and explanations."""
    result = {}
    
    # Define criteria to extract
    criteria = ["smooth_score", "flexibility_score", "quality_score", "comforting_score"]
    
    # Extract ratings and explanations for each criterion
    for criterion in criteria:
        # Extract from first-level tags
        rating = extract_tool_arguments(response, criterion, "rating")
        explanation = extract_tool_arguments(response, criterion, "explanation")
        
        if rating and explanation:
            try:
                result[criterion] = {
                    "rating": int(rating[0]),
                    "explanation": explanation[0]
                }
            except (ValueError, IndexError) as e:
                print(f"Error parsing {criterion}: {e}")
                print(f"Rating: {rating}, Explanation: {explanation}")
    
    # Print the extracted data for debugging
    print(f"Extracted evaluation data: {json.dumps(result, indent=2)}")
    
    return result

async def evaluate_interview(user_id: str, session_id: Optional[int] = None) -> Dict[str, Any]:
    """Evaluate the interview experience from a user's perspective."""
    
    # Setup paths
    logs_dir = Path(os.getenv("LOGS_DIR", "logs"))
    
    # If session_id is not provided, find the most recent session
    if session_id is None:
        user_dir = logs_dir / user_id / "execution_logs"
        if not user_dir.exists():
            raise FileNotFoundError(f"User directory not found: {user_dir}")
        
        session_dirs = [d for d in user_dir.iterdir() if d.is_dir() \
                         and d.name.startswith("session_")]
        if not session_dirs:
            raise FileNotFoundError(f"No session directories found for user {user_id}")
        
        # Extract session numbers and find the highest
        session_numbers = [int(d.name.split("_")[1]) for d in session_dirs]
        session_id = max(session_numbers)
        print(f"Using most recent session: {session_id}")
    
    chat_history_path = user_dir / f"session_{session_id}" / "chat_history.log"
    
    # Check if chat history exists
    if not chat_history_path.exists():
        raise FileNotFoundError(f"Chat history not found at {chat_history_path}")
    
    # Read chat history
    with open(chat_history_path, "r", encoding="utf-8") as f:
        chat_history = f.read()
    
    # Format prompt
    prompt = format_evaluation_prompt(chat_history)
    
    # Get engine
    engine = get_engine()
    
    # Call engine
    print(f"Evaluating interview for user {user_id}, session {session_id}...")
    response = invoke_engine(engine, prompt)
    
    # Parse response
    try:
        evaluation = parse_evaluation_response(response)
        
        # Setup evaluation logger
        eval_logger = EvaluationLogger.setup_logger(user_id, session_id)
        
        # Log evaluation
        timestamp = datetime.now()
        eval_logger.log_prompt_response(
            evaluation_type="user_experience",
            prompt=prompt,
            response=response,
            timestamp=timestamp
        )
        
        # Log evaluation results to CSV
        eval_logger.log_user_experience_evaluation(
            evaluation_data=evaluation,
            timestamp=timestamp
        )
        
        print(f"Evaluation completed for user {user_id}, session {session_id}")
        
        return evaluation
    
    except Exception as e:
        print(f"Error parsing evaluation response: {str(e)}")
        print("Raw response:", response)
        raise

async def main_async():
    parser = argparse.ArgumentParser(description="Evaluate interview experience from a user's perspective")
    parser.add_argument("--user_id", required=True, help="User ID")
    parser.add_argument("--session_id", type=int, help="Session ID (optional, uses most recent if not provided)")
    
    args = parser.parse_args()
    
    try:
        await evaluate_interview(args.user_id, args.session_id)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
