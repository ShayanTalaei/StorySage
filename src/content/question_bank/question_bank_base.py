from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import os
import json
import random
import string
from datetime import datetime

from content.question_bank.question import Question

class QuestionBankBase(ABC):
    """Abstract base class for question bank implementations.
    
    This class defines the standard interface that all question bank implementations
    must follow. Concrete implementations (e.g., VectorDB, GraphDB) should inherit
    from this class and implement the abstract methods.
    """
    
    def __init__(self):
        self.questions: List[Question] = []
    
    def generate_question_id(self) -> str:
        """Generate a short, unique question ID.
        Format: Q_MMDDHHMM_{random_chars}
        Example: Q_03121423_X7K (March 12, 14:23)
        """
        timestamp = datetime.now().strftime("%m%d%H%M")
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
        return f"Q_{timestamp}_{random_chars}"
    
    @abstractmethod
    def add_question(
        self,
        content: str,
        memory_ids: List[str] = None,
    ) -> Question:
        """Add a new question to the database.
        
        Args:
            content: The question text
            memory_ids: List of related memory IDs
            
        Returns:
            Question: The created question object
        """
        pass
    
    @abstractmethod
    def search_questions(
        self, 
        query: str, 
        k: int = 5
    ) -> List[Dict]:
        """Search for similar questions.
        
        Args:
            query: The search query text
            k: Number of results to return
            
        Returns:
            List[Dict]: List of question dictionaries with similarity scores
        """
        pass
    
    def link_memory(self, question_id: str, memory_id: str) -> None:
        """Link a memory to a question."""
        question = self.get_question_by_id(question_id)
        if question and memory_id not in question.memory_ids:
            question.memory_ids.append(memory_id)
    
    def get_question_by_id(self, question_id: str) -> Optional[Question]:
        """Get a question by its ID."""
        return next((q for q in self.questions if q.id == question_id), None)
    
    def save_to_file(self, user_id: str) -> None:
        """Save the question bank to file."""
        content_data = {
            'questions': [question.to_dict() for question in self.questions]
        }
        
        content_filepath = os.getenv("LOGS_DIR") + f"/{user_id}/question_bank_content.json"
        os.makedirs(os.path.dirname(content_filepath), exist_ok=True)
        
        with open(content_filepath, 'w') as f:
            json.dump(content_data, f, indent=2)
            
        self._save_implementation_specific(user_id)
    
    @abstractmethod
    def _save_implementation_specific(self, user_id: str) -> None:
        """Save implementation-specific data."""
        pass
    
    @classmethod
    def load_from_file(cls, user_id: str) -> 'QuestionBankBase':
        """Load a question bank from file."""
        question_bank = cls()
        
        content_filepath = os.getenv("LOGS_DIR") + f"/{user_id}/question_bank_content.json"
        
        try:
            with open(content_filepath, 'r') as f:
                content_data = json.load(f)
                
            for question_data in content_data['questions']:
                question = Question.from_dict(question_data)
                question_bank.questions.append(question)
                
            question_bank._load_implementation_specific(user_id)
                
        except FileNotFoundError:
            question_bank.save_to_file(user_id)
            
        return question_bank
    
    @abstractmethod
    def _load_implementation_specific(self, user_id: str) -> None:
        """Load implementation-specific data."""
        pass 