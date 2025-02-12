from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import os
import json
import random
import string
from datetime import datetime

from content.memory_bank.memory import Memory

class MemoryBankBase(ABC):
    """Abstract base class for memory bank implementations.
    
    This class defines the standard interface that all memory bank implementations
    must follow. Concrete implementations (e.g., VectorDB, GraphRAG) should inherit
    from this class and implement the abstract methods.
    """
    
    def __init__(self):
        self.memories: List[Memory] = []
    
    def generate_memory_id(self) -> str:
        """Generate a short, unique memory ID.
        Format: MEM_MMDDHHMM_{random_chars}
        Example: MEM_03121423_X7K (March 12, 14:23)
        """
        timestamp = datetime.now().strftime("%m%d%H%M")
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
        return f"MEM_{timestamp}_{random_chars}"
    
    @abstractmethod
    def add_memory(
        self,
        title: str,
        text: str,
        importance_score: int,
        source_interview_response: str,
        metadata: Optional[Dict] = None,
        question_ids: Optional[List[str]] = None
    ) -> Memory:
        """Add a new memory to the database.
        
        Args:
            title: Title of the memory
            text: Content of the memory
            importance_score: Importance score of the memory
            source_interview_response: Original response from interview
            metadata: Optional metadata dictionary
            question_ids: Optional list of question IDs that generated this memory
            
        Returns:
            Memory: The created memory object
        """
        pass
    
    @abstractmethod
    def search_memories(self, query: str, k: int = 5) -> List[Dict]:
        """Search for similar memories using the query text.
        
        Args:
            query: The search query text
            k: Number of results to return
            
        Returns:
            List[Dict]: List of memory dictionaries with similarity scores
        """
        pass
    
    def save_to_file(self, user_id: str) -> None:
        """Save the memory bank to file.
        
        Args:
            user_id: ID of the user whose memories are being saved
        """
        content_data = {
            'memories': [memory.to_dict() for memory in self.memories]
        }
        
        content_filepath = os.getenv("LOGS_DIR") + f"/{user_id}/memory_bank_content.json"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(content_filepath), exist_ok=True)
        
        with open(content_filepath, 'w') as f:
            json.dump(content_data, f, indent=2)
            
        # Implementation-specific save
        self._save_implementation_specific(user_id)
    
    @abstractmethod
    def _save_implementation_specific(self, user_id: str) -> None:
        """Save implementation-specific data (e.g., embeddings, graph structure).
        
        Args:
            user_id: ID of the user whose data is being saved
        """
        pass
    
    @classmethod
    def load_from_file(cls, user_id: str) -> 'MemoryBankBase':
        """Load a memory bank from file.
        
        Args:
            user_id: ID of the user whose memories to load
            
        Returns:
            MemoryBankBase: Loaded memory bank instance
        """
        memory_bank = cls()
        
        content_filepath = os.getenv("LOGS_DIR") + f"/{user_id}/memory_bank_content.json"
        
        try:
            # Load content
            with open(content_filepath, 'r') as f:
                content_data = json.load(f)
                
            # Reconstruct memories
            for memory_data in content_data['memories']:
                memory = Memory.from_dict(memory_data)
                memory_bank.memories.append(memory)
                
            # Load implementation-specific data
            memory_bank._load_implementation_specific(user_id)
                
        except FileNotFoundError:
            # Create new empty memory bank if files don't exist
            memory_bank.save_to_file(user_id)
            
        return memory_bank
    
    @abstractmethod
    def _load_implementation_specific(self, user_id: str) -> None:
        """Load implementation-specific data (e.g., embeddings, graph structure).
        
        Args:
            user_id: ID of the user whose data to load
        """
        pass
    
    def get_memory_by_id(self, memory_id: str) -> Optional[Memory]:
        """Get a memory by its ID."""
        return next((m for m in self.memories if m.id == memory_id), None)

    def link_question(self, memory_id: str, question_id: str) -> None:
        """Link a question to a memory.
        
        Args:
            memory_id: ID of the memory
            question_id: ID of the question to link
        """
        memory = self.get_memory_by_id(memory_id)
        if memory and question_id not in memory.question_ids:
            memory.question_ids.append(question_id)

    def get_memories_by_question(self, question_id: str) -> List[Memory]:
        """Get all memories linked to a specific question.
        
        Args:
            question_id: ID of the question
            
        Returns:
            List[Memory]: List of memories linked to the question
        """
        return [m for m in self.memories if question_id in m.question_ids] 