from datetime import datetime
from pydantic import BaseModel


class Memory(BaseModel):
    id: str
    title: str
    text: str
    metadata: dict
    importance_score: int
    timestamp: datetime
    source_interview_response: str

    def to_dict(self) -> dict:
        """Convert Memory object to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'text': self.text,
            'metadata': self.metadata,
            'importance_score': self.importance_score,
            'timestamp': self.timestamp.isoformat(),
            'source_interview_response': self.source_interview_response,
        }

    @classmethod
    def from_dict(cls, memory_dict: dict) -> 'Memory':
        """Create Memory object from dictionary."""
        return cls(
            id=memory_dict['id'],
            title=memory_dict['title'],
            text=memory_dict['text'],
            metadata=memory_dict['metadata'],
            importance_score=memory_dict['importance_score'],
            timestamp=datetime.fromisoformat(memory_dict['timestamp']),
            source_interview_response=memory_dict['source_interview_response'],
        )
