from pathlib import Path
import sys
import argparse
import csv
from typing import List, Dict
import json

# Add the src directory to Python path
src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from content.biography.biography import Biography, Section
from content.memory_bank.memory_bank_vector_db import VectorMemoryBank
from utils.llm.engines import get_engine, invoke_engine

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
- Unsubstantiated Claims: List any claims or statements that aren't supported by the memories
- Missing Details: List any important details from the memories that should be included
- Overall Assessment: A brief explanation of your evaluation

Format your response as a JSON object with these exact keys:
{{
    "groundness_score": number,
    "unsubstantiated_claims": list of strings,
    "missing_details": list of strings,
    "overall_assessment": string
}}"""

def evaluate_section_groundness(
    section: Section,
    memory_bank: VectorMemoryBank,
    engine
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
    
    # Parse response
    evaluation = json.loads(output)
    return {
        "section_id": section.id,
        "section_title": section.title,
        "evaluation": evaluation
    }

def evaluate_biography_groundness(
    biography: Biography,
    memory_bank: VectorMemoryBank,
    engine
) -> List[Dict]:
    """Evaluate groundness for all sections in a biography."""
    results = []
    
    def process_section(section: Section):
        # Evaluate current section
        if section.content and section.memory_ids:
            result = evaluate_section_groundness(section, memory_bank, engine)
            results.append(result)
        
        # Process subsections
        for subsection in section.subsections.values():
            process_section(subsection)
    
    process_section(biography.root)
    return results

def save_results_to_csv(results: List[Dict], filename: str):
    """Save evaluation results to CSV file."""
    
    # Ensure results directory exists
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Section ID',
            'Section Title',
            'Groundness Score',
            'Unsubstantiated Claims',
            'Missing Details',
            'Overall Assessment'
        ])
        
        for result in results:
            eval_dict = result['evaluation']  # Already parsed JSON
            writer.writerow([
                result['section_id'],
                result['section_title'],
                eval_dict['groundness_score'],
                '; '.join(eval_dict['unsubstantiated_claims']),
                '; '.join(eval_dict['missing_details']),
                eval_dict['overall_assessment']
            ])
    
    print(f"Results saved to: {filename}")

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
    engine = get_engine("gpt-4o-mini")
    
    # Load biography and memory bank
    biography = Biography.load_from_file(args.user_id)
    memory_bank = VectorMemoryBank.load_from_file(args.user_id)
    
    # Run evaluation
    print(f"Evaluating biography groundness for user: {args.user_id}")
    results = evaluate_biography_groundness(biography, memory_bank, engine)
    
    # Save results
    filename = f"logs/{args.user_id}/evaluations/groundness_{biography.version}.csv"
    save_results_to_csv(results, filename)

if __name__ == "__main__":
    main() 