from abc import ABC, abstractmethod
from typing import List, Optional
import os
import json
import random
import string
from datetime import datetime
import xml.etree.ElementTree as ET

from content.question_bank.question import Question, QuestionSearchResult
from utils.llm.engines import get_engine, invoke_engine
from utils.logger.evaluation_logger import EvaluationLogger

from dotenv import load_dotenv

load_dotenv()

from content.question_bank.duplicate_detection_prompt import QUESTION_SIMILARITY_PROMPT

class QuestionBankBase(ABC):
    """Abstract base class for question bank implementations.
    
    This class defines the standard interface that all question bank implementations
    must follow. Concrete implementations (e.g., VectorDB, GraphDB) should inherit
    from this class and implement the abstract methods.
    """
    
    def __init__(self):
        self.questions: List[Question] = []
        self.engine = get_engine("gpt-4o")
    
    def generate_question_id(self) -> str:
        """Generate a short, unique question ID.
        Format: Q_MMDDHHMM_{random_chars}
        Example: Q_03121423_X7K (March 12, 14:23)
        """
        timestamp = datetime.now().strftime("%m%d%H%M")
        random_chars = ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=3))
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
        k: int = 3
    ) -> List[QuestionSearchResult]:
        """Search for similar questions.
        
        Args:
            query: The search query text
            k: Number of results to return
            
        Returns:
            List[QuestionSearchResult]: List of question search results with similarity scores
        """
        pass
    
    def save_to_file(self, user_id: str) -> None:
        """Save the question bank to file."""
        content_data = {
            'questions': [question.to_dict() for question in self.questions]
        }
        
        content_filepath = os.getenv("LOGS_DIR") + \
            f"/{user_id}/question_bank_content.json"
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
        
        content_filepath = os.getenv("LOGS_DIR") + \
            f"/{user_id}/question_bank_content.json"
        
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
    
    def get_question_by_id(self, question_id: str) -> Optional[Question]:
        """Get a question by its ID."""
        return next((q for q in self.questions if q.id == question_id), None)
    
    def link_memory(self, question_id: str, memory_id: str) -> None:
        """Link a memory to a question."""
        question = self.get_question_by_id(question_id)
        if question and memory_id not in question.memory_ids:
            question.memory_ids.append(memory_id)
    
    def get_questions_by_memory(self, memory_id: str) -> List[Question]:
        """Get all questions linked to a specific memory."""
        return [q for q in self.questions if memory_id in q.memory_ids]
    
    def evaluate_question_duplicate(self, target_question: str, proposer: str = "unknown") -> tuple:
        """Check if a question is semantically equivalent to existing questions.
        
        Args:
            target_question: The question to evaluate
            proposer: The agent proposing the question
            
        Returns:
            tuple: (is_duplicate, matched_question, explanation)
                - is_duplicate: Boolean indicating if the question is a duplicate
                - matched_question: The matched question if duplicate, 
                    empty string if not
                - explanation: Explanation of the evaluation
        """
        # Get similar questions
        similar_results = self.search_questions(target_question)
        
        if not similar_results:
            return (False, "", "No similar questions found")
            
        # Format similar questions for prompt
        similar_questions = "\n\n".join([
            f"<question>{result.content}</question>\n"
            for result in similar_results
        ])
        
        # Prepare prompt
        prompt = QUESTION_SIMILARITY_PROMPT.format(
            target_question=target_question,
            similar_questions=similar_questions
        )
        
        # Get evaluation from LLM and parse response
        output = invoke_engine(self.engine, prompt)
        
        # Parse XML response
        root = ET.fromstring(output)
        is_duplicate = root.find('is_duplicate').text.lower() == 'true'
        matched_question = root.find('matched_question').text
        explanation = root.find('explanation').text
        
        # Convert matched_question to empty string if "null"
        matched_question = "" if matched_question == "null" else matched_question
        
        # Log evaluation results using current logger
        logger = EvaluationLogger.get_current_logger()
        if logger:
            logger.log_question_similarity(
                target_question=target_question,
                similar_questions=[r.content for r in similar_results],
                similarity_scores=[r.similarity_score for r in similar_results],
                is_duplicate=is_duplicate,
                matched_question=matched_question,
                explanation=explanation,
                proposer=proposer
            )
        
        return (is_duplicate, matched_question, explanation)