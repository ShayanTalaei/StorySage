import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime
import asyncio
from typing import Dict, Any, Optional, List
import random

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
        "guidelines": [
            "- Ensure transitions are smooth and natural.",
            "- Avoid unnecessary transitions when the current topic isn't fully explored and the user remains engaged.",
            "- Avoid reverting to previous topics or introducing new ones during an ongoing story.",
            "- Only switch topics if the user shows disinterest (e.g., giving brief responses or wanting to skip questions).",
            "- Avoid repetitive questions on the same topic.",
            "- Prefer concrete questions over overly open-ended ones that are difficult to answer."
        ]
    },
    "flexibility_score": {
        "description": "How flexible was the interview process in adapting to user responses",
        "guidelines": [
            "- Allow the user to ask questions and express thoughts, while avoiding too many broad, high-level questions."
            "- Adapt flexibly to user responses and ask deeper follow-up questions.",
            "- Change topics if the user shows disinterest in the current one.",
        ]
    },
    "comforting_score": {
        "description": "How comfortable and natural the interview experience felt",
        "guidelines": [
            "- Respond to the user's emotions and feelings.",
            "- Create a supportive environment by engaging deeply with the user's experiences and allowing space for detailed storytelling."
        ]
    }
}

INTERVIEW_EVALUATION_INSTRUCTIONS = """
You are an expert in conversation analysis and therapeutic dialogue. You will be given two interview transcripts (A and B) to compare. Your task is to evaluate them based on specific criteria and vote for the better one in each category.

Please carefully read through both interviews and then vote based on these criteria:

{criteria_text}

For each criterion:
1. Vote for either Interview A, Interview B, or "Tie" if they are equally good
2. Provide a detailed explanation (2-3 sentences) justifying your choice with specific examples from both interviews

Important: If the interviews are difficult to compare or show similar quality for any criterion, don't hesitate to vote "Tie". A tie is a perfectly valid outcome when the differences are minimal or unclear.

Your evaluation should be objective, fair, and based solely on the interviews provided. Do not try to guess which system generated which interview.
"""

INTERVIEW_EVALUATION_IO = """
## Input Context

Interview A:
<A>
{interview_a_content}
</A>

Interview B:
<B>
{interview_b_content}
</B>

## Output Format
Use the tool calls to output your evaluation.

Reminder: 
- Just specify A, B, or Tie for the voting, other formats like "Interviewer A", "Interviewer B", "model_A", "model_B", "version_Tie", are not allowed.
- Just specify A, B, or Tie!!!
- Wrap your output in <tool_calls>...</tool_calls> tags!!!
- Wrap your output in <tool_calls>...</tool_calls> tags!!!

<tool_calls>
<smooth_score>
    <explanation>Your explanation comparing both interviews</explanation>
    <voting>A or B or Tie</voting>
</smooth_score>

<flexibility_score>
    <explanation>Your explanation comparing both interviews</explanation>
    <voting>A or B or Tie</voting>
</flexibility_score>

<comforting_score>
    <explanation>Your explanation comparing both interviews</explanation>
    <voting>A or B or Tie</voting>
</comforting_score>
</tool_calls>
"""

def format_evaluation_prompt(interview_a_content: str, interview_b_content: str) -> str:
    """Format the evaluation prompt with the interview content."""
    criteria_text = ""
    for criterion, details in EVALUATION_CRITERIA.items():
        criteria_text += (f"- {criterion.replace('_', ' ').title()}: "
                f"{details['description']}\n")
        for guideline in details['guidelines']:
            criteria_text += f"  * {guideline}\n"
        criteria_text += "\n"
    
    instructions = INTERVIEW_EVALUATION_INSTRUCTIONS.format(criteria_text=criteria_text)
    io_format = INTERVIEW_EVALUATION_IO.format(
        interview_a_content=interview_a_content,
        interview_b_content=interview_b_content
    )
    
    return f"{instructions}\n\n{io_format}"

def parse_evaluation_response(response: str) -> Dict[str, Any]:
    """Parse the evaluation response to extract ratings and explanations."""
    result = {}
    
    # Define criteria to extract
    criteria = ["smooth_score", "flexibility_score", "comforting_score"]
    
    # Extract ratings and explanations for each criterion
    for criterion in criteria:
        # Extract from first-level tags
        voting = extract_tool_arguments(response, criterion, "voting")
        explanation = extract_tool_arguments(response, criterion, "explanation")
        
        if voting and explanation:
            try:
                # Normalize voting value to handle different formats
                vote_value = voting[0].strip()
                # Convert to standard format (A, B, or Tie)
                if vote_value.lower() in ['a', 'interview a']:
                    vote_value = 'A'
                elif vote_value.lower() in ['b', 'interview b']:
                    vote_value = 'B'
                elif vote_value.lower() in ['tie', 'equal', 'both']:
                    vote_value = 'Tie'
                
                result[criterion] = {
                    "voting": vote_value,
                    "explanation": explanation[0]
                }
            except (ValueError, IndexError) as e:
                print(f"Error parsing {criterion}: {e}")
                print(f"Voting: {voting}, Explanation: {explanation}")
    
    # Print the extracted data for debugging
    print(f"Extracted evaluation data: {json.dumps(result, indent=2)}")
    
    return result

async def get_interview_content(user_id: str, session_id: int, model_name: Optional[str] = None) -> str:
    """Get the interview content from chat history.
    
    Args:
        user_id: User ID
        session_id: Session ID
        model_name: Optional model name for loading from baseline directories
        
    Returns:
        Interview content from chat history with timestamps and log levels removed
    """
    # Determine the base path based on model name
    if model_name:
        base_dir = f"logs_{model_name}"
    else:
        base_dir = os.getenv("LOGS_DIR", "logs")
    
    chat_history_path = Path(base_dir) / user_id / "execution_logs" / \
        f"session_{session_id}" / "chat_history.log"
    
    # Check if chat history exists
    if not chat_history_path.exists():
        raise FileNotFoundError(f"Chat history not found at {chat_history_path}")
    
    # Read first 200 lines of chat history and clean up the format
    cleaned_lines = []
    with open(chat_history_path, "r", encoding="utf-8") as f:
        lines = f.readlines()[:200]
        for line in lines:
            # Remove timestamp and log level using split
            parts = line.split(" - INFO - ", 1)
            if len(parts) > 1:
                cleaned_lines.append(parts[1])
            else:
                cleaned_lines.append(line)  # Keep original line if pattern not found
    
    return "".join(cleaned_lines)

async def prepare_interview_pairs(user_id: str, session_id: int) -> List[Dict[str, Any]]:
    """Prepare pairs of interviews (ours vs baselines) for voting.
    
    Args:
        user_id: User ID
        session_id: Session ID
        
    Returns:
        List of interview pairs with metadata
    """
    pairs = []
    
    # Get our interview content
    our_interview = await get_interview_content(user_id, session_id)
    
    # Get baseline interviews from model-specific directories
    for dir_name in os.listdir('.'):
        if dir_name.startswith('logs_'):
            # Extract and normalize model name
            model_name = dir_name[5:]  # Remove 'logs_' prefix
            
            try:
                baseline_interview = await get_interview_content(
                    user_id, 
                    session_id,
                    model_name=model_name
                )
                
                # Randomly assign positions (A or B) for fair comparison
                if random.random() < 0.5:
                    pair = {
                        'interview_A': our_interview,
                        'interview_B': baseline_interview,
                        'model_A': 'ours',
                        'model_B': model_name
                    }
                else:
                    pair = {
                        'interview_A': baseline_interview,
                        'interview_B': our_interview,
                        'model_A': model_name,
                        'model_B': 'ours'
                    }
                pairs.append(pair)
                
            except Exception as e:
                print(f"Error loading baseline interview for {model_name}: {e}")
                continue
    
    return pairs

async def evaluate_interview_pair(user_id: str, session_id: int, pair: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
    """Evaluate a pair of interviews through comparative voting.
    
    Args:
        user_id: User ID
        session_id: Session ID
        pair: Dictionary containing interview pair data
        max_retries: Maximum number of retry attempts (default: 3)
        
    Returns:
        Evaluation results
    """
    retries = 0
    while retries < max_retries:
        try:
            # Format prompt
            prompt = format_evaluation_prompt(
                interview_a_content=pair['interview_A'],
                interview_b_content=pair['interview_B']
            )
            
            # Get engine
            engine = get_engine("gemini-2.0-flash", temperature=0.5)
            
            # Call engine
            print(f"Evaluating interview pair for user {user_id}, "
                  f"session {session_id} (attempt {retries + 1}/{max_retries})...")
            response = invoke_engine(engine, prompt)
            
            # Parse response
            evaluation = parse_evaluation_response(response)
            
            # Add metadata to evaluation results
            evaluation['metadata'] = {
                'model_A': pair['model_A'],
                'model_B': pair['model_B']
            }
            
            # Setup evaluation logger
            eval_logger = EvaluationLogger.setup_logger(user_id, session_id)
            
            # Log evaluation
            timestamp = datetime.now()
            eval_logger.log_prompt_response(
                evaluation_type="interview_content_comparison",
                prompt=prompt,
                response=response,
                timestamp=timestamp
            )
            
            # Log comparative evaluation results
            eval_logger.log_interview_comparison_evaluation(
                evaluation_data=evaluation,
                timestamp=timestamp
            )
            
            return evaluation
            
        except Exception as e:
            retries += 1
            if retries >= max_retries:
                print(f"Failed after {max_retries} attempts. Final error: {str(e)}")
                raise
            print(f"Attempt {retries}/{max_retries} failed: {str(e)}. Retrying...")
            await asyncio.sleep(1)  # Add a small delay between retries

async def main_async():
    parser = argparse.ArgumentParser(
        description="Evaluate interview experience through comparison")
    parser.add_argument("--user_id", required=True, help="User ID")
    parser.add_argument(
        "--session_id", type=int, 
        help="Session ID (optional, uses the first session if not provided)",
        default=1
    )
    
    args = parser.parse_args()
    
    try:
        print(f"Comparing session: {args.session_id}")

        # If session_id is not provided, find the most recent session
        user_dir = Path(os.getenv("LOGS_DIR", "logs")) / \
                args.user_id / "execution_logs"
        if not user_dir.exists():
            raise FileNotFoundError(f"User directory not found: {user_dir}")
        
        session_dirs = [d for d in user_dir.iterdir() if d.is_dir() \
                            and d.name.startswith("session_")]
        if not session_dirs:
            raise FileNotFoundError(f"No session directories"
                                    f" found for user {args.user_id}")
        
        # Prepare interview pairs
        print(f"\nPreparing interview pairs for user {args.user_id}...")
        pairs = await prepare_interview_pairs(args.user_id, args.session_id)
        
        if not pairs:
            print("No interview pairs Found for comparison")
            return
            
        # Evaluate each pair
        print(f"\nFound {len(pairs)} pairs for comparison")
        
        for i, pair in enumerate(pairs, 1):
            print(f"\nEvaluating pair {i} of {len(pairs)}:")
            print(f"Model A: {pair['model_A']}")
            print(f"Model B: {pair['model_B']}")
            
            evaluation = await evaluate_interview_pair(args.user_id, 
                                                       args.session_id, pair)
            
            print(f"\nComparison {i} completed")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
