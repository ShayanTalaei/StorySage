from pathlib import Path
import sys
import argparse
from typing import List, Dict

# Add the src directory to Python path
src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from content.biography.biography import Biography, Section
from content.memory_bank.memory_bank_vector_db import VectorMemoryBank
from utils.llm.engines import get_engine, invoke_engine
from utils.logger.evaluation_logger import EvaluationLogger
from utils.llm.xml_formatter import extract_tool_arguments

GROUNDNESS_PROMPT = """\
You are an expert at evaluating if biographical text is grounded in source memories.

Given a biography section and its source memories, evaluate if the biographical text is substantiated by the memories.

Biography Section:
<section_text>
{section_text}
</section_text>

Source Memories:
<memories>
{memories_xml}
</memories>

Please analyze if each statement in the biography section is supported by the source memories.
Return your evaluation in this format:
- Groundness Score (0-100): A score indicating what percentage of the biographical content is substantiated by the memories
- Overall Assessment: A brief explanation of your evaluation
- Unsubstantiated Claims: List any claims or statements in the biography section that aren't supported by the memories
- Unsubstantiated Details Explanation: List of explanation of why the claims in the biography section are unsubstantiated

Return your evaluation using the following tool call format:

<tool_calls>
    <evaluate_groundness>
        <groundness_score>number between 0-100</groundness_score>
        <unsubstantiated_claims>["claim 1", "claim 2", ...]</unsubstantiated_claims>
        <unsubstantiated_details_explanation>["explanation 1", "explanation 2", ...]</unsubstantiated_details_explanation>
        <overall_assessment>Your brief explanation of the evaluation</overall_assessment>
    </evaluate_groundness>
</tool_calls>
"""

def evaluate_section_groundness(
    section: Section,
    memory_bank: VectorMemoryBank,
    engine,
    logger: EvaluationLogger,
    biography_version: int
) -> Dict:
    """Evaluate how well a section's content is grounded in its source memories."""
    # Get formatted memories
    memories_xml = memory_bank.get_formatted_memories_from_ids(
        section.memory_ids,
        include_source=True
    )
    
    # Prepare prompt
    prompt = GROUNDNESS_PROMPT.format(
        section_text=section.content,
        memories_xml=memories_xml
    )
    
    # Get evaluation using the engine
    output = invoke_engine(engine, prompt)

    # Parse response using XML formatter with error handling
    try:
        groundness_scores = extract_tool_arguments(
            output, "evaluate_groundness", "groundness_score")
        groundness_score = groundness_scores[0] if groundness_scores else 0

        claims = extract_tool_arguments(
            output, "evaluate_groundness", "unsubstantiated_claims")
        unsubstantiated_claims = claims[0] if claims else []

        details = extract_tool_arguments(
            output, "evaluate_groundness", "unsubstantiated_details_explanation")
        unsubstantiated_details_explanation = details[0] if details else []

        assessments = extract_tool_arguments(
            output, "evaluate_groundness", "overall_assessment")
        overall_assessment = assessments[0] if assessments else "No assessment provided"

    except Exception as e:
        print(f"Error parsing evaluation response: {str(e)}")
        # Provide default values if parsing fails
        groundness_score = 0
        unsubstantiated_claims = []
        unsubstantiated_details_explanation = []
        overall_assessment = "Failed to parse evaluation response"
    
    result = {
        "section_id": section.id,
        "section_title": section.title,
        "evaluation": {
            "groundness_score": groundness_score,
            "unsubstantiated_claims": unsubstantiated_claims,
            "unsubstantiated_details_explanation": unsubstantiated_details_explanation,
            "overall_assessment": overall_assessment
        }
    }
    
    # Log evaluation results
    if logger:  # Allow None logger for testing/reuse
        logger.log_biography_groundness(
            section_id=section.id,
            section_title=section.title,
            groundness_score=groundness_score,
            unsubstantiated_claims=unsubstantiated_claims,
            unsubstantiated_details_explanation=unsubstantiated_details_explanation,
            overall_assessment=overall_assessment,
            biography_version=biography_version
        )
    
    return result

def evaluate_biography_groundness(
    biography: Biography,
    memory_bank: VectorMemoryBank,
    engine
) -> List[Dict]:
    """Evaluate groundness for all sections in a biography."""
    results = []
    logger = EvaluationLogger(user_id=biography.user_id)
    
    def process_section(section: Section):
        # Evaluate current section
        if section.content and section.memory_ids:
            result = evaluate_section_groundness(
                section, 
                memory_bank, 
                engine, 
                logger,
                biography.version
            )
            results.append(result)
        
        # Process subsections
        for subsection in section.subsections.values():
            process_section(subsection)
    
    process_section(biography.root)
    return results

def main():
    """Main function to run the biography groundness evaluation."""
    parser = argparse.ArgumentParser(
        description='Evaluate biography groundness for a given user'
    )
    parser.add_argument(
        '--user_id',
        type=str,
        help='ID of the user whose biography to evaluate',
        required=True
    )
    
    args = parser.parse_args()
    
    # Initialize LLM engine
    engine = get_engine("gpt-4o")
    
    # Load biography and memory bank
    biography = Biography.load_from_file(args.user_id)
    memory_bank = VectorMemoryBank.load_from_file(args.user_id)
    
    # Run evaluation
    print(f"Evaluating biography groundness for user: {args.user_id}")
    evaluate_biography_groundness(biography, memory_bank, engine)
    print("Evaluation complete. Results saved to logs directory.")

if __name__ == "__main__":
    main() 