import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime
import asyncio
from typing import Dict, Any, Optional
import csv

# Add the src directory to Python path
src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from dotenv import load_dotenv
from utils.llm.engines import get_engine, invoke_engine
from utils.logger.evaluation_logger import EvaluationLogger
from utils.llm.xml_formatter import extract_tool_arguments
from content.biography.biography import Biography

load_dotenv()

# Evaluation criteria
EVALUATION_CRITERIA = {
    "insightfulness_score": {
        "description": "Reveals profound perspectives on the subject's experiences and motivations, offering readers meaningful interpretations beyond surface facts",
        "scale": "0-5",
        "guidelines": [
            "0: Completely superficial, only lists basic facts with no interpretation",
            "1: Mostly superficial with minimal interpretation of experiences",
            "2: Some attempt at interpretation but lacks depth and meaningful insights",
            "3: Good balance of facts and interpretation with some meaningful insights",
            "4: Strong insights that reveal deeper motivations and perspectives",
            "5: Exceptional insights that profoundly illuminate the subject's life and character"
        ]
    },
    "narrativity_score": {
        "description": "Employs compelling storytelling techniques that engage readers through vivid description, appropriate pacing, and emotional resonance",
        "scale": "0-5",
        "guidelines": [
            "0: No narrative structure, just a list of disconnected facts",
            "1: Basic chronology but lacks storytelling elements and engagement",
            "2: Some storytelling elements but lacks vivid description or emotional resonance",
            "3: Good narrative flow with some vivid descriptions and emotional elements",
            "4: Strong storytelling with engaging descriptions and consistent emotional resonance",
            "5: Masterful storytelling with captivating descriptions, perfect pacing, and powerful emotional impact"
        ]
    },
    "coherence_score": {
        "description": "Presents a logical flow of events with clear chronology, establishing meaningful connections between life phases while maintaining narrative continuity",
        "scale": "0-5",
        "guidelines": [
            "0: Completely disjointed with no logical flow or connections",
            "1: Mostly disconnected sections with unclear chronology",
            "2: Basic chronology but weak connections between life phases",
            "3: Clear chronology with some meaningful connections between events",
            "4: Strong logical flow with well-established connections between life phases",
            "5: Exceptional coherence with seamless transitions and profound connections across the entire life story"
        ]
    }
}

BIOGRAPHY_EVALUATION_INSTRUCTIONS = """
You are an expert literary critic specializing in biographies. You will be given a complete biography to evaluate for its content quality. Your task is to assess the biography based on specific criteria.

Please carefully read through the entire biography and then provide ratings and explanations for the following criteria:

{criteria_text}

For each criterion, provide:
1. A numerical rating based on the scale
2. A detailed explanation (2-3 sentences) justifying your rating with specific examples from the biography

Your evaluation should be objective, fair, and based solely on the biography provided.
"""

BIOGRAPHY_EVALUATION_IO = """
## Input Context

Biography:
<biography>
{biography_content}
</biography>

## Output Format
Use the tool calls to output your evaluation.

<tool_calls>
<insightfulness_score>
    <rating>[0-5]</rating>
    <explanation>Your explanation here</explanation>
</insightfulness_score>
<narrativity_score>
    <rating>[0-5]</rating>
    <explanation>Your explanation here</explanation>
</narrativity_score>
<coherence_score>
    <rating>[0-5]</rating>
    <explanation>Your explanation here</explanation>
</coherence_score>
</tool_calls>
"""

def format_evaluation_prompt(biography_content: str) -> str:
    """Format the evaluation prompt with the biography content."""
    
    criteria_text = ""
    for criterion, details in EVALUATION_CRITERIA.items():
        criteria_text += (f"- {criterion.replace('_', ' ').title()}: "
                f"{details['description']}. Rate from {details['scale']}.\n")
        for guideline in details['guidelines']:
            criteria_text += f"  * {guideline}\n"
        criteria_text += "\n"
    
    instructions = BIOGRAPHY_EVALUATION_INSTRUCTIONS.format(criteria_text=criteria_text)
    io_format = BIOGRAPHY_EVALUATION_IO.format(biography_content=biography_content)
    
    return f"{instructions}\n\n{io_format}"

def parse_evaluation_response(response: str) -> Dict[str, Any]:
    """Parse the evaluation response to extract ratings and explanations."""
    result = {}
    
    # Define criteria to extract
    criteria = ["insightfulness_score", "narrativity_score", "coherence_score"]
    
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

async def get_biography_markdown(user_id: str, biography_version: Optional[int] = None) -> tuple:
    """Get the biography content in markdown format.
    
    Args:
        user_id: User ID
        biography_version: Optional biography version (uses latest if not provided)
        
    Returns:
        Tuple of (biography content in markdown format, actual version used)
    """
    # Load the biography
    biography = Biography.load_from_file(user_id, version=biography_version or -1)
    
    # Export to markdown
    markdown_content = await biography.export_to_markdown()
    
    return markdown_content, biography.version

async def evaluate_biography(user_id: str, biography_version: Optional[int] = None) -> Dict[str, Any]:
    """Evaluate the entire biography for content quality.
    
    Args:
        user_id: User ID
        biography_version: Optional biography version (uses latest if not provided)
        
    Returns:
        Evaluation results
    """
    try:
        # Get biography content in markdown format
        biography_content, actual_version = await get_biography_markdown(user_id, biography_version)
        
        # Format prompt
        prompt = format_evaluation_prompt(biography_content)
        
        # Get engine
        engine = get_engine()
        
        # Call engine
        print(f"Evaluating biography for user {user_id}, version {actual_version}...")
        response = invoke_engine(engine, prompt)
        
        # Parse response
        evaluation = parse_evaluation_response(response)
        
        # Setup evaluation logger
        eval_logger = EvaluationLogger.setup_logger(user_id)
        
        # Log evaluation
        timestamp = datetime.now()
        eval_logger.log_prompt_response(
            evaluation_type="biography_content",
            prompt=prompt,
            response=response,
            timestamp=timestamp
        )
        
        # Log evaluation results to CSV
        eval_logger.log_biography_content_evaluation(
            evaluation_data=evaluation,
            biography_version=actual_version,
            timestamp=timestamp
        )
        
        print(f"Content evaluation completed for biography version {actual_version}")
        
        return evaluation
    
    except Exception as e:
        print(f"Error evaluating biography: {str(e)}")
        raise

async def main_async():
    parser = argparse.ArgumentParser(description="Evaluate biography content quality")
    parser.add_argument("--user_id", required=True, help="User ID")
    parser.add_argument("--biography_version", type=int, help="Biography version (optional, uses latest if not provided)")
    
    args = parser.parse_args()
    
    try:
        await evaluate_biography(args.user_id, args.biography_version)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
