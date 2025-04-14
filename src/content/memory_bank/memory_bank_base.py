from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import os
import json
import random
import string
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from content.memory_bank.memory import Memory, MemorySearchResult

class MemoryBankBase(ABC):
    """Abstract base class for memory bank implementations.
    
    This class defines the standard interface that all memory bank implementations
    must follow. Concrete implementations (e.g., VectorDB, GraphRAG) should inherit
    from this class and implement the abstract methods.
    """
    
    def __init__(self):
        self.memories: List[Memory] = []
        self.session_id: Optional[str] = None
    
    def set_session_id(self, session_id: str) -> None:
        """Set the current session ID for the memory bank.
        
        Args:
            session_id: The ID of the current interview session
        """
        self.session_id = session_id
    
    def generate_memory_id(self) -> str:
        """Generate a short, unique memory ID.
        Format: MEM_MMDDHHMM_{random_chars}
        Example: MEM_03121423_X7K (March 12, 14:23)
        """
        timestamp = datetime.now().strftime("%m%d%H%M")
        random_chars = ''.join(random.choices(string.ascii_uppercase 
                                              + string.digits, k=3))
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
    def search_memories(self, query: str, k: int = 5) -> List[MemorySearchResult]:
        """Search for similar memories using the query text.
        
        Args:
            query: The search query text
            k: Number of results to return
            
        Returns:
            List[MemorySearchResult]: List of memory search results 
            with similarity scores
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
        
        # Save to the main user directory
        content_filepath = os.getenv("LOGS_DIR") + \
            f"/{user_id}/memory_bank_content.json"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(content_filepath), exist_ok=True)
        
        with open(content_filepath, 'w') as f:
            json.dump(content_data, f, indent=2)
        
        # Implementation-specific save for main directory
        self._save_implementation_specific(user_id)
        
        # If session_id is provided, save an additional copy in the session directory
        if self.session_id:
            session_filepath = os.getenv("LOGS_DIR") + \
                f"/{user_id}/execution_logs/session_{self.session_id}/" + \
                "memory_bank_content.json"
            os.makedirs(os.path.dirname(session_filepath), exist_ok=True)
            
            with open(session_filepath, 'w') as f:
                json.dump(content_data, f, indent=2)
                
            # Implementation-specific save for session directory
            session_path = f"{user_id}/execution_logs/session_{self.session_id}"
            self._save_implementation_specific(session_path)
    
    @abstractmethod
    def _save_implementation_specific(self, path: str) -> None:
        """Save implementation-specific data (e.g., embeddings, graph structure).
        
        Args:
            user_id: ID of the user whose data is being saved
        """
        pass
    
    @classmethod
    def load_from_file(cls, user_id: str, base_path: Optional[str] = None) -> 'MemoryBankBase':
        """Load a memory bank from file.
        
        Args:
            user_id: ID of the user whose memories to load
            base_path: Optional base path to load from (e.g. session directory)
            
        Returns:
            MemoryBankBase: Loaded memory bank instance
        """
        memory_bank = cls()
        
        # Determine content filepath based on base_path
        if base_path:
            content_filepath = os.path.join(base_path, "memory_bank_content.json")
        else:
            content_filepath = os.getenv("LOGS_DIR") + \
                f"/{user_id}/memory_bank_content.json"
        
        try:
            # Load content
            with open(content_filepath, 'r') as f:
                content_data = json.load(f)
                
            # Reconstruct memories
            for memory_data in content_data['memories']:
                memory = Memory.from_dict(memory_data)
                memory_bank.memories.append(memory)
                
            # Load implementation-specific data
            memory_bank._load_implementation_specific(user_id, base_path)
                
        except FileNotFoundError:
            # Create new empty memory bank if files don't exist
            memory_bank.save_to_file(user_id)
            
        return memory_bank
    
    @abstractmethod
    def _load_implementation_specific(self, user_id: str, base_path: Optional[str] = None) -> None:
        """Load implementation-specific data (e.g., embeddings, graph structure).
        
        Args:
            user_id: ID of the user whose data to load
            base_path: Optional base path to load from (e.g. session directory)
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

    def get_formatted_memories_from_ids(self, memory_ids: List[str], include_source: bool = True) -> str:
        """Get and format memories from memory IDs into XML format.
        
        Args:
            memory_ids: List of memory IDs to format
            include_source: Whether to include source interview response in output
            
        Returns:
            str: XML formatted string of memories, or empty string if no memories
        """
        if not memory_ids:
            return ""
            
        # Track seen source responses to avoid duplicates
        seen_sources = {}  # source_text -> first_memory_id
        memory_texts = []
        
        for memory_id in memory_ids:
            memory = self.get_memory_by_id(memory_id)
            if not memory:
                continue
                
            if include_source:
                source_text = memory.source_interview_response
                if source_text in seen_sources:
                    # Reference the first memory with this source
                    source_xml = (
                        f'<source_interview_response>\n'
                        f'Same as {seen_sources[source_text]}\n'
                        f'</source_interview_response>'
                    )
                else:
                    # First time seeing this source
                    seen_sources[source_text] = memory.id
                    source_xml = (
                        f'<source_interview_response>\n'
                        f'{source_text}\n'
                        f'</source_interview_response>'
                    )
                
                # Build memory XML with modified source
                memory_xml = [
                    '<memory>',
                    f'<title>{memory.title}</title>',
                    f'<summary>{memory.text}</summary>',
                    f'<id>{memory.id}</id>',
                    source_xml,
                    '</memory>'
                ]
                memory_texts.append('\n'.join(memory_xml))
            else:
                memory_texts.append(memory.to_xml(include_source=False))
        
        return "\n\n".join(memory_texts) if memory_texts else ""
