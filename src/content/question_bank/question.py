from datetime import datetime
from pydantic import BaseModel

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