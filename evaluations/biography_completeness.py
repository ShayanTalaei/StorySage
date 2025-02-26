from pathlib import Path
from typing import List, Set
import argparse
import sys

# Add the src directory to Python path
src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from content.biography.biography import Biography, Section
from content.memory_bank.memory_bank_vector_db import VectorMemoryBank
from utils.logger.evaluation_logger import EvaluationLogger

def extract_memory_ids_from_biography(biography: Biography) -> Set[str]:
    """Extract all unique memory IDs referenced in the biography.
    
    Args:
        biography: Biography object to analyze
        
    Returns:
        Set[str]: Set of unique memory IDs found in the biography
    """
    memory_ids = set()
    
    def process_section(section: Section):
        # Add memory IDs from current section
        memory_ids.update(section.memory_ids)
        
        # Process subsections recursively
        for subsection in section.subsections.values():
            process_section(subsection)
    
    process_section(biography.root)
    return memory_ids

def calculate_biography_completeness(user_id: str, logger: EvaluationLogger, biography_version: int) -> dict:
    """Calculate biography completeness metrics based on memory coverage."""
    # Load latest biography and memory bank
    biography = Biography.load_from_file(user_id)
    memory_bank = VectorMemoryBank.load_from_file(user_id)
    
    # Get all memory IDs from biography
    biography_memory_ids = extract_memory_ids_from_biography(biography)
    
    # Get all memory IDs from memory bank
    all_memory_ids = {memory.id for memory in memory_bank.memories}
    
    # Calculate metrics
    referenced_count = len(biography_memory_ids)
    total_memories = len(all_memory_ids)
    
    # Calculate recall (percentage of memories covered)
    recall = referenced_count / total_memories if total_memories > 0 else 0
    
    # Find memories not referenced in biography
    unreferenced_memories = all_memory_ids - biography_memory_ids
    
    metrics = {
        "memory_recall": round(recall * 100, 2),  # Convert to percentage
        "total_memories": total_memories,
        "referenced_memories": referenced_count,
        "unreferenced_memories": list(unreferenced_memories)
    }
    
    # Get details for unreferenced memories
    unreferenced_details = get_unreferenced_memory_details(user_id)
    
    # Log evaluation results
    if logger:  # Allow None logger for testing/reuse
        logger.log_biography_completeness(
            metrics=metrics,
            unreferenced_details=unreferenced_details,
            biography_version=biography_version
        )
    
    return metrics

def get_unreferenced_memory_details(user_id: str) -> List[dict]:
    """Get details of memories not referenced in the biography."""
    # Get unreferenced memory IDs
    biography = Biography.load_from_file(user_id)
    biography_memory_ids = extract_memory_ids_from_biography(biography)
    memory_bank = VectorMemoryBank.load_from_file(user_id)
    all_memory_ids = {memory.id for memory in memory_bank.memories}
    unreferenced_ids = all_memory_ids - biography_memory_ids
    
    # Get details for each unreferenced memory
    unreferenced_details = []
    for memory_id in unreferenced_ids:
        memory = memory_bank.get_memory_by_id(memory_id)
        if memory:
            unreferenced_details.append({
                "id": memory.id,
                "title": memory.title,
                "importance_score": memory.importance_score
            })
    
    # Sort first by importance score (highest first), then by ID
    return sorted(
        unreferenced_details,
        key=lambda x: (x["id"])
    )

def main():
    """Main function to run the biography completeness evaluation."""
    parser = argparse.ArgumentParser(
        description='Evaluate biography completeness for a given user'
    )
    parser.add_argument(
        '--user_id',
        type=str,
        help='ID of the user whose biography to evaluate',
        required=True
    )
    
    args = parser.parse_args()
    
    # Load biography to get version
    biography = Biography.load_from_file(args.user_id)
    
    # Initialize logger
    logger = EvaluationLogger(user_id=args.user_id)
    
    # Run evaluation
    print(f"Evaluating biography completeness for user: {args.user_id}")
    calculate_biography_completeness(args.user_id, logger, biography.version)
    print("Evaluation complete. Results saved to logs directory.")

if __name__ == "__main__":
    main()
