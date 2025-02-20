from datetime import datetime
from typing import List
from pydantic import BaseModel, Field

class Question(BaseModel):
    """Model for storing interview questions with their associated memories."""
    id: str
    content: str
    memory_ids: list[str]  # IDs of memories related to this question
    timestamp: datetime

    def to_dict(self) -> dict:
        """Convert Question object to dictionary."""
        return {
            'id': self.id,
            'content': self.content,
            'memory_ids': self.memory_ids,
            'timestamp': self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, question_dict: dict) -> 'Question':
        """Create Question object from dictionary."""
        return cls(
            id=question_dict['id'],
            content=question_dict['content'],
            memory_ids=question_dict['memory_ids'],
            timestamp=datetime.fromisoformat(question_dict['timestamp'])
        )

class QuestionSearchResult(Question):
    """Model for question search results that includes similarity score."""
    similarity_score: float = Field(ge=0, le=1)  # Score between 0 and 1

    @classmethod
    def from_question(cls, question: Question, similarity_score: float) -> 'QuestionSearchResult':
        """Create a search result from a Question object and similarity score."""
        return cls(
            id=question.id,
            content=question.content,
            memory_ids=question.memory_ids,
            timestamp=question.timestamp,
            similarity_score=similarity_score
        )

class SimilarQuestionsGroup(BaseModel):
    """Model for grouping a proposed question with its similar existing questions."""
    proposed: str
    similar: List[QuestionSearchResult] 