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

GROUNDEDNESS_INSTRUCTIONS = r"""
You are an expert at evaluating if biographical text is grounded in source memories.

## Task

Given a biography section and its source memories, evaluate if the biographical text is substantiated by the memories. Return a score between 0-100, indicating what percentage of the biographical content is substantiated by the memories.

## Groundedness Definition

Let's define groundedness mathematically:

1. Let \(S = \{s_1, s_2, \ldots, s_n\}\) be the set of atomic information units from source memories.
2. Let \(B = \{b_1, b_2, \ldots, b_m\}\) be the set of atomic claims/statements in the biography section.
3. Define \(B_{\text{substantiated}} = \{b_i \in B \mid b_i \text{ can be derived from or substantiated by any } s_j \in S\}\).
4. The groundedness score is calculated as:

\[ \text{Groundedness Score} = \frac{|B_{\text{substantiated}}|}{|B|} \times 100 \]
"""

GROUNDEDNESS_IO = r"""
## Input Context

Biography Section:
<section_text>
{section_text}
</section_text>

Source Memories:
<memories>
{memories_xml}
</memories>

## Output Format

Return your evaluation using the following tool call format:

<thinking>
Step 1: Decompose source memories into atomic information units
- Source Memory 1: [List atomic information units]
- Source Memory 2: [List atomic information units]
...

Step 2: Decompose biography section into atomic claims/statements
- Claim 1: [Statement]
- Claim 2: [Statement]
...

Step 3: Evaluate each claim against source information
- Claim 1: [Substantiated/Unsubstantiated] - [Reasoning]
- Claim 2: [Substantiated/Unsubstantiated] - [Reasoning]
...

Step 4: Calculate groundedness score
- Total claims: [Number]
- Substantiated claims: [Number]
- Groundedness score: [Calculation] = [Final percentage]

Step 5: Summarize overall assessment
[Your overall assessment of the biography section's groundedness]
</thinking>

<tool_calls>
    <evaluate_groundedness>
        <groundedness_score>number between 0-100</groundedness_score>
        <unsubstantiated_claims>["claim 1", "claim 2", ...]</unsubstantiated_claims>
        <unsubstantiated_details_explanation>["explanation 1", "explanation 2", ...]</unsubstantiated_details_explanation>
        <overall_assessment>Your brief explanation of the evaluation</overall_assessment>
    </evaluate_groundedness>
</tool_calls>
"""

def evaluate_section_groundedness(
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
    prompt = GROUNDEDNESS_INSTRUCTIONS + GROUNDEDNESS_IO.format(
        section_text=section.content,
        memories_xml=memories_xml
    )
    
    # Get evaluation using the engine
    output = invoke_engine(engine, prompt)

    # Log prompt and response separately
    logger.log_prompt_response(
        evaluation_type=f"biography_groundedness_section_{section.id}",
        prompt=prompt,
        response=output
    )

    # Parse response using XML formatter with error handling
    try:
        groundedness_scores = extract_tool_arguments(
            output, "evaluate_groundedness", "groundedness_score")
        groundedness_score = groundedness_scores[0] \
              if groundedness_scores else 0

        claims = extract_tool_arguments(
            output, "evaluate_groundedness", "unsubstantiated_claims")
        unsubstantiated_claims = claims[0] if claims else []

        details = extract_tool_arguments(
            output, "evaluate_groundedness", "unsubstantiated_details_explanation")
        unsubstantiated_details_explanation = details[0] if details else []

        assessments = extract_tool_arguments(
            output, "evaluate_groundedness", "overall_assessment")
        overall_assessment = assessments[0] if assessments \
              else "No assessment provided"

    except Exception as e:
        print(f"Error parsing evaluation response: {str(e)}")
        # Provide default values if parsing fails
        groundedness_score = 0
        unsubstantiated_claims = []
        unsubstantiated_details_explanation = []
        overall_assessment = "Failed to parse evaluation response"
    
    result = {
        "section_id": section.id,
        "section_title": section.title,
        "evaluation": {
            "groundedness_score": groundedness_score,
            "unsubstantiated_claims": unsubstantiated_claims,
            "unsubstantiated_details_explanation": \
                unsubstantiated_details_explanation,
            "overall_assessment": overall_assessment
        }
    }
    
    # Log evaluation results
    if logger:  # Allow None logger for testing/reuse
        logger.log_biography_section_groundedness(
            section_id=section.id,
            section_title=section.title,
            groundedness_score=groundedness_score,
            unsubstantiated_claims=unsubstantiated_claims,
            unsubstantiated_details_explanation=\
                unsubstantiated_details_explanation,
            overall_assessment=overall_assessment,
            biography_version=biography_version
        )
    
    return result

def evaluate_biography_groundedness(
    biography: Biography,
    memory_bank: VectorMemoryBank,
    engine
) -> List[Dict]:
    """Evaluate groundedness for all sections in a biography."""
    results = []
    logger = EvaluationLogger(user_id=biography.user_id)
    
    def process_section(section: Section):
        # Evaluate current section
        if section.content and section.memory_ids:
            result = evaluate_section_groundedness(
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

def calculate_overall_groundedness(results: List[Dict]) -> float:
    """Calculate the overall groundedness score for the entire biography.
    
    Args:
        results: List of section evaluation results
        
    Returns:
        float: Average groundedness score across all sections
    """
    if not results:
        return 0.0
    
    total_score = 0
    for result in results:
        score = result["evaluation"]["groundedness_score"]
        # Convert to float if it's a string
        if isinstance(score, str):
            try:
                score = float(score)
            except ValueError:
                score = 0
        total_score += score
    
    return total_score / len(results)

def main():
    """Main function to run the biography groundedness evaluation."""
    parser = argparse.ArgumentParser(
        description='Evaluate biography groundedness for a given user'
    )
    parser.add_argument(
        '--user_id',
        type=str,
        help='ID of the user whose biography to evaluate',
        required=True
    )
    parser.add_argument(
        '--version',
        type=int,
        help='Version of the biography to evaluate',
        required=False,
        default=-1
    )
    
    args = parser.parse_args()
    
    # Initialize LLM engine
    engine = get_engine("gpt-4o")
    
    # Load biography and memory bank
    biography = Biography.load_from_file(args.user_id, args.version)
    memory_bank = VectorMemoryBank.load_from_file(args.user_id)
    
    # Run evaluation
    print(f"Evaluating biography groundedness for user: {args.user_id}")
    results = evaluate_biography_groundedness(biography, memory_bank, engine)
    
    # Calculate and print overall groundedness score
    overall_score = calculate_overall_groundedness(results)
    print(f"\nOverall Biography Groundedness Score: {overall_score:.2f}%")
    
    # Log overall score using the logger
    logger = EvaluationLogger(user_id=args.user_id)
    logger.log_biography_overall_groundedness(
        overall_score=overall_score,
        section_scores=results,
        biography_version=biography.version
    )
    
    print("Evaluation complete. Results saved to logs directory.")

if __name__ == "__main__":
    main() 