from pathlib import Path
from typing import List, Set
import argparse
import sys

# Add the src directory to Python path
src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from content.biography.biography import Biography, Section
from content.memory_bank.memory_bank_vector_db import VectorMemoryBank

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

def calculate_biography_completeness(user_id: str) -> dict:
    """Calculate biography completeness metrics based on memory coverage.
    
    Args:
        user_id: ID of the user whose biography to evaluate
        
    Returns:
        dict: Dictionary containing completeness metrics:
            - memory_recall: Percentage of memories covered
            - total_memories: Total number of memories in bank
            - referenced_memories: Number of memories referenced in biography
            - unreferenced_memories: List of memory IDs not referenced in biography
    """
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
    
    return {
        "memory_recall": round(recall * 100, 2),  # Convert to percentage
        "total_memories": total_memories,
        "referenced_memories": referenced_count,
        "unreferenced_memories": list(unreferenced_memories)
    }

def get_unreferenced_memory_details(user_id: str) -> List[dict]:
    """Get details of memories not referenced in the biography.
    
    Args:
        user_id: ID of the user whose biography to evaluate
        
    Returns:
        List[dict]: List of dictionaries containing details of unreferenced memories:
            - id: Memory ID
            - title: Memory title
            - importance_score: Memory importance score
    """
    # Get unreferenced memory IDs
    completeness_metrics = calculate_biography_completeness(user_id)
    unreferenced_ids = completeness_metrics["unreferenced_memories"]
    
    # Load memory bank
    memory_bank = VectorMemoryBank.load_from_file(user_id)
    
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
    
    # Sort by importance score (highest first)
    return sorted(unreferenced_details, 
                 key=lambda x: x["importance_score"], 
                 reverse=True)

def print_completeness_report(user_id: str) -> None:
    """Print a detailed report of biography completeness.
    
    Args:
        user_id: ID of the user whose biography to evaluate
    """
    # Get metrics
    metrics = calculate_biography_completeness(user_id)
    unreferenced_details = get_unreferenced_memory_details(user_id)
    
    # Print report
    print(f"Biography Completeness Report for User: {user_id}")
    print("-" * 50)
    print(f"Memory Coverage: {metrics['memory_recall']}%")
    print(f"Total Memories: {metrics['total_memories']}")
    print(f"Referenced Memories: {metrics['referenced_memories']}")
    print(f"Unreferenced Memories: {len(metrics['unreferenced_memories'])}")
    
    if unreferenced_details:
        print("\nUnreferenced Memories (sorted by importance):")
        print("-" * 50)
        for memory in unreferenced_details:
            print(f"ID: {memory['id']}")
            print(f"Title: {memory['title']}")
            print(f"Importance Score: {memory['importance_score']}")
            print("-" * 30)

def main():
    """Main function to run the biography completeness evaluation."""
    parser = argparse.ArgumentParser(
        description='Evaluate biography completeness for a given user'
    )
    parser.add_argument(
        '--user_id',
        type=str,
        help='ID of the user whose biography to evaluate',
        default=None
    )
    
    args = parser.parse_args()
    
    print_completeness_report(args.user_id)

if __name__ == "__main__":
    main()
