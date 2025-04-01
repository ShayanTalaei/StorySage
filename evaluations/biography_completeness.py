from pathlib import Path
from typing import List, Set
import argparse
import sys
import os

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

def calculate_biography_completeness(user_id: str, logger: EvaluationLogger, biography_version: int = -1) -> dict:
    """Calculate biography completeness metrics based on memory coverage."""
    # Load biography and memory bank
    biography = Biography.load_from_file(user_id, biography_version)
    
    # Determine memory bank path based on version
    if biography_version > 0:
        # For specific version, load from session directory
        base_path = os.path.join(os.getenv("LOGS_DIR"), user_id, "execution_logs", f"session_{biography_version}")
        memory_bank = VectorMemoryBank.load_from_file(user_id, base_path=base_path)
    else:
        # For latest version, load from default path
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
    unreferenced_details = get_unreferenced_memory_details(user_id, biography_version)
    
    # Log evaluation results
    if logger:  # Allow None logger for testing/reuse
        logger.log_biography_completeness(
            metrics=metrics,
            unreferenced_details=unreferenced_details,
            biography_version=biography.version
        )
    
    return metrics

def get_unreferenced_memory_details(user_id: str, version: int = -1) -> List[dict]:
    """Get details of memories not referenced in the biography."""
    # Get unreferenced memory IDs
    biography = Biography.load_from_file(user_id, version)
    biography_memory_ids = extract_memory_ids_from_biography(biography)
    
    # Determine memory bank path based on version
    if version > 0:
        # For specific version, load from session directory
        base_path = os.path.join(os.getenv("LOGS_DIR"), user_id, "execution_logs", f"session_{version}")
        memory_bank = VectorMemoryBank.load_from_file(user_id, base_path=base_path)
    else:
        # For latest version, load from default path
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
                "importance_score": memory.importance_score,
                "timestamp": memory.timestamp
            })
    
    # Sort first by importance score (highest first), then by ID
    return sorted(
        unreferenced_details,
        key=lambda x: (x["timestamp"])
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
    parser.add_argument(
        '--version',
        type=int,
        help='Version of the biography to evaluate',
        required=False,
        default=-1
    )
    
    args = parser.parse_args()
    
    # Initialize logger
    logger = EvaluationLogger(user_id=args.user_id)
    
    # Run evaluation
    print(f"Evaluating biography completeness for user: {args.user_id}")
    calculate_biography_completeness(args.user_id, logger, args.version)
    print("Evaluation complete. Results saved to logs directory.")

if __name__ == "__main__":
    main()
