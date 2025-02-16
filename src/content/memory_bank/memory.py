from datetime import datetime
from typing import List
from pydantic import BaseModel


class Memory(BaseModel):
    """Model for storing memories with their associated questions."""
    id: str
    title: str
    text: str
    metadata: dict
    importance_score: int
    timestamp: datetime
    source_interview_response: str
    question_ids: List[str] = []  # IDs of questions that generated this memory

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
            'question_ids': self.question_ids
        }

    def to_xml(self, include_source: bool = False) -> str:
        """Convert memory to XML format string without source handling.
        
        Args:
            include_source: Whether to include source_interview_response
        Returns:
            str: XML formatted string of the memory
        """
        lines = [
            '<memory>',
            f'<title>{self.title}</title>',
            f'<summary>{self.text}</summary>',
            f'<id>{self.id}</id>'
        ]
        
        if include_source:
            lines.append(
                f'<source_interview_response>\n'
                f'{self.source_interview_response}\n'
                f'</source_interview_response>'
            )
                
        lines.append('</memory>')
        return '\n'.join(lines)

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
            question_ids=memory_dict.get('question_ids', [])
        )
