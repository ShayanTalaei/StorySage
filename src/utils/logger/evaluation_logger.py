from pathlib import Path
import csv
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

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
        matched_question: str,
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
            matched_question: Content of the matched duplicate question
            explanation: Explanation of the similarity evaluation
            proposer: Name of the agent proposing this question
            timestamp: Optional timestamp (defaults to current time)
        """
        # Construct filename based on session_id
        if self.session_id is not None:
            filename = self.eval_dir / \
                f"question_similarity_session_{self.session_id}.csv"
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
                    'Matched Question',
                    'Explanation'
                ])
            
            writer.writerow([
                timestamp.isoformat(),
                proposer,
                target_question,
                '; '.join(similar_questions),
                '; '.join(f"{score:.2f}" for score in similarity_scores),
                is_duplicate,
                matched_question,
                explanation
            ])

    def log_biography_groundedness(
        self,
        section_id: str,
        section_title: str,
        groundedness_score: int,
        unsubstantiated_claims: List[str],
        unsubstantiated_details_explanation: List[str],
        overall_assessment: str,
        biography_version: int,
        prompt: str = None,
        response: str = None
    ) -> None:
        """Log biography groundedness evaluation results."""
        # Create a version-specific directory
        version_dir = self.eval_dir / f"biography_{biography_version}"
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # Log to CSV file
        filename = version_dir / "groundedness_summary.csv"
        file_exists = filename.exists()
        
        with open(filename, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    'Section ID',
                    'Section Title',
                    'Groundedness Score',
                    'Overall Assessment',
                    'Unsubstantiated Claims',
                    'Missing Details',
                ])
            
            writer.writerow([
                section_id,
                section_title,
                groundedness_score,
                overall_assessment,
                '; '.join(unsubstantiated_claims),
                '; '.join(unsubstantiated_details_explanation),
            ])
        
        # Log prompt and response to a log file if provided
        if prompt or response:
            log_filename = version_dir / f"section_{section_id}.log"
            with open(log_filename, 'w', encoding='utf-8') as log_file:
                if prompt:
                    log_file.write("=== PROMPT ===\n\n")
                    log_file.write(prompt)
                    log_file.write("\n\n")
                
                if response:
                    log_file.write("=== RESPONSE ===\n\n")
                    log_file.write(response)
                    log_file.write("\n\n")

    def log_biography_completeness(
        self,
        metrics: Dict[str, Any],
        unreferenced_details: List[Dict[str, Any]],
        biography_version: int
    ) -> None:
        """Log biography completeness evaluation results."""
        # Create a version-specific directory
        version_dir = self.eval_dir / f"biography_{biography_version}"
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # Log to CSV file
        filename = version_dir / "completeness_summary.csv"
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Metric', 'Value'])
            
            writer.writerow(['Memory Coverage', f"{metrics['memory_recall']}%"])
            writer.writerow(['Total Memories', metrics['total_memories']])
            writer.writerow(['Referenced Memories', 
                             metrics['referenced_memories']])
            writer.writerow(['Unreferenced Memories Count', 
                             len(metrics['unreferenced_memories'])])
            
            if unreferenced_details:
                writer.writerow([])  # Empty row for separation
                writer.writerow(['Unreferenced Memory ID', 
                                 'Title', 'Importance Score'])
                for memory in unreferenced_details:
                    writer.writerow([
                        memory['id'],
                        memory['title'],
                        memory['importance_score']
                    ])

    def log_prompt_response(
        self,
        evaluation_type: str,
        prompt: str,
        response: str,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Log prompt and response for an evaluation.
        
        Args:
            evaluation_type: Type of evaluation 
                (e.g., 'question_similarity', 'groundness')
            prompt: The prompt sent to the LLM
            response: The response received from the LLM
            timestamp: Optional timestamp (defaults to current time)
        """
        # Create a logs directory for prompts and responses
        logs_dir = self.eval_dir / "prompt_response_logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # Create a timestamped filename
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        filename = logs_dir / f"{evaluation_type}_{timestamp_str}.log"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"=== TIMESTAMP: {timestamp.isoformat()} ===\n\n")
            f.write("=== PROMPT ===\n\n")
            f.write(prompt)
            f.write("\n\n=== RESPONSE ===\n\n")
            f.write(response)
            f.write("\n")

    def log_response_latency(
        self,
        message_id: str,
        user_message_timestamp: datetime,
        response_timestamp: datetime
    ) -> None:
        """Log the latency between user message and system response.
        
        Args:
            message_id: Unique identifier for the message pair
            user_message_timestamp: When the user sent their message
            response_timestamp: When the response was delivered
        """
        # Create a logs directory for response latency
        logs_dir = self.eval_dir / "response_latency"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Calculate latency in seconds
        latency_seconds = (response_timestamp - user_message_timestamp).total_seconds()
        
        # Log to CSV file
        filename = logs_dir / "response_latency.csv"
        file_exists = filename.exists()
        
        with open(filename, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    'Message ID',
                    'Timestamp',
                    'Latency (seconds)'
                ])
            
            writer.writerow([
                message_id,
                user_message_timestamp.isoformat(),
                f"{latency_seconds:.3f}"
            ]) 