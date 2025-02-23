from pathlib import Path
import csv
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

class EvaluationLogger:
    """Logger for evaluation results."""
    
    _current_logger = None
    
    def __init__(self, user_id: Optional[str] = None, session_id: Optional[int] = None):
        """Initialize evaluation logger.
        
        Args:
            user_id: Optional user ID to organize logs by user
            session_id: Optional session ID for session-based logging
        """
        self.user_id = user_id
        self.session_id = session_id
        self.base_dir = Path(os.getenv("LOGS_DIR", "logs"))
        
        # Create evaluations directory
        if user_id:
            if session_id is not None:
                self.eval_dir = self.base_dir / user_id / "evaluations" / \
                    f"session_{session_id}"
            else:
                self.eval_dir = self.base_dir / user_id / "evaluations"
        else:
            self.eval_dir = self.base_dir / "evaluations"
        self.eval_dir.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_current_logger(cls) -> Optional['EvaluationLogger']:
        """Get the current logger instance."""
        return cls._current_logger
    
    @classmethod
    def setup_logger(
        cls,
        user_id: str,
        session_id: Optional[int] = None
    ) -> 'EvaluationLogger':
        """Setup a new evaluation logger.
        
        Args:
            user_id: User identifier
            session_id: Optional session identifier
        """
        logger = cls(user_id=user_id, session_id=session_id)
        cls._current_logger = logger
        return logger

    def log_question_similarity(
        self,
        target_question: str,
        similar_questions: List[str],
        similarity_scores: List[float],
        is_duplicate: bool,
        matching_id: str,
        explanation: str,
        proposer: str = "unknown",
        timestamp: Optional[datetime] = None
    ) -> None:
        """Log question similarity evaluation results.
        
        Args:
            target_question: The question being evaluated
            similar_questions: List of similar questions found
            similarity_scores: List of similarity scores
            is_duplicate: Whether the question is considered a duplicate
            matching_id: ID of the matching question (if duplicate)
            explanation: Explanation of the similarity evaluation
            proposer: Name of the agent proposing this question
            timestamp: Optional timestamp (defaults to current time)
        """
        # Construct filename based on session_id
        if self.session_id is not None:
            filename = self.eval_dir / \
                f"question_similarity_evaluations_session_{self.session_id}.csv"
        else:
            filename = self.eval_dir / "question_similarity_evaluations.csv"
            
        file_exists = filename.exists()
        
        if timestamp is None:
            timestamp = datetime.now()
            
        with open(filename, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    'Timestamp',
                    'Proposer',
                    'Target Question',
                    'Similar Questions',
                    'Similarity Scores',
                    'Is Duplicate',
                    'Matching Question ID',
                    'Explanation'
                ])
            
            writer.writerow([
                timestamp.isoformat(),
                proposer,
                target_question,
                '; '.join(similar_questions),
                '; '.join(f"{score:.2f}" for score in similarity_scores),
                is_duplicate,
                matching_id if matching_id != 'null' else '',
                explanation
            ])

    def log_biography_groundness(
        self,
        section_id: str,
        section_title: str,
        groundness_score: int,
        unsubstantiated_claims: List[str],
        missing_details: List[str],
        overall_assessment: str,
        biography_version: int
    ) -> None:
        """Log biography groundness evaluation results."""
        filename = self.eval_dir / f"groundness_{biography_version}.csv"
        file_exists = filename.exists()
        
        with open(filename, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    'Section ID',
                    'Section Title',
                    'Groundness Score',
                    'Unsubstantiated Claims',
                    'Missing Details',
                    'Overall Assessment'
                ])
            
            writer.writerow([
                section_id,
                section_title,
                groundness_score,
                '; '.join(unsubstantiated_claims),
                '; '.join(missing_details),
                overall_assessment
            ])

    def log_biography_completeness(
        self,
        metrics: Dict[str, Any],
        unreferenced_details: List[Dict[str, Any]],
        biography_version: int
    ) -> None:
        """Log biography completeness evaluation results."""
        filename = self.eval_dir / f"completeness_{biography_version}.csv"
        file_exists = filename.exists()
        
        with open(filename, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Metric', 'Value'])
            
            writer.writerow(['Memory Coverage', f"{metrics['memory_recall']}%"])
            writer.writerow(['Total Memories', metrics['total_memories']])
            writer.writerow(['Referenced Memories', metrics['referenced_memories']])
            writer.writerow(['Unreferenced Memories Count', 
                             len(metrics['unreferenced_memories'])])
            
            if unreferenced_details:
                writer.writerow([])  # Empty row for separation
                writer.writerow(['Unreferenced Memory ID', 'Title', 'Importance Score'])
                for memory in unreferenced_details:
                    writer.writerow([
                        memory['id'],
                        memory['title'],
                        memory['importance_score']
                    ]) 