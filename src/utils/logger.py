import logging
import pathlib
import os
from typing import List, Optional
from dotenv import load_dotenv
import threading

load_dotenv(override=True)
LOGS_DIR = os.getenv("LOGS_DIR")

LOG_LEVELS = {
    "info": {
        "log_level": logging.INFO,
        "color": "\033[37m"  # White
    },
    "warning": {
        "log_level": logging.WARNING,
        "color": "\033[95m"  # Pink
    },
    "error": {
        "log_level": logging.ERROR,
        "color": "\033[91m"  # Red
    }
}

class SessionLogger:
    _file_locks = {}
    _locks_lock = threading.Lock()
    _current_logger = None
    
    @classmethod
    def log_to_file(cls, file_name: str, message: str, log_level: str = "info") -> None:
        """
        Logs a message to a specific file within the session's execution_logs directory.
        
        Args:
            file_name: Name of the log file (without .log extension)
            message: Message to log
        """
        # Get the current instance's logger
        current_logger = cls.get_current_logger()
        if not current_logger:
            raise RuntimeError("No logger has been initialized. Call setup_logger or setup_default_logger first.")
            
        # Create logger for this specific file
        logger_id = f"{current_logger.user_id}_{current_logger.session_id or current_logger.log_type}_{file_name}"
        file_logger = logging.getLogger(logger_id)
        
        # Define log directory and file path
        if current_logger.session_id:
            # Session-based logging
            log_dir = current_logger.log_dir / "execution_logs" / f"session_{current_logger.session_id}"
        else:
            # Non-session logging
            log_dir = current_logger.log_dir / current_logger.log_type
        
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{file_name}.log"
        
        if not file_logger.handlers:
            file_logger.setLevel(current_logger.log_level)
            
            # Setup file handler
            file_handler = logging.FileHandler(log_file)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            file_logger.addHandler(file_handler)
            
            # Add console handler if this file should output to console
            if current_logger.console_output_files and file_name in current_logger.console_output_files:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                file_logger.addHandler(console_handler)
                
                # Print colored message to console
                color = LOG_LEVELS[log_level]["color"]
                reset = "\033[0m"
                print(f"{color}{message}{reset}")
        
        # Get or create lock for this file
        if log_file not in cls._file_locks:
            with cls._locks_lock:
                file_lock = cls._file_locks.get(log_file)
                if file_lock is None:
                    file_lock = threading.Lock()
                    cls._file_locks[log_file] = file_lock
        else:
            file_lock = cls._file_locks[log_file]
        
        # Use the lock when writing to file
        with file_lock:
            file_logger.log(LOG_LEVELS[log_level]["log_level"], message)

    @classmethod
    def get_current_logger(cls):
        return cls._current_logger

    def __init__(self, user_id: str, session_id: Optional[int] = None, log_type: str = None, 
                 log_level=logging.INFO, console_output_files: List[str] = None):
        self.user_id = user_id
        self.session_id = session_id
        self.log_type = log_type
        self.log_level = log_level
        self.console_output_files = console_output_files
        
        # Store this instance as the current logger
        SessionLogger._current_logger = self
        
        # Setup base logger
        logger_id = f"{'session' if session_id else log_type}_{user_id}_{session_id or ''}"
        self.logger = logging.getLogger(logger_id)
        
        if not self.logger.handlers:
            self.logger.setLevel(log_level)
            
            # Base log directory
            self.log_dir = pathlib.Path(LOGS_DIR) / user_id
            
            if self.console_output_files:
                console_handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)

def setup_default_logger(
    user_id: str,
    log_type: str = "user_edits",
    log_level: int = logging.INFO,
    console_output_files: Optional[List[str]] = None
) -> SessionLogger:
    """Setup a logger for operations without an active session.
    
    Args:
        user_id: User identifier
        log_type: Type of logging (default: "user_edits")
        log_level: Logging level (default: logging.INFO)
        console_output_files: List of file names to output to console
    """
    return SessionLogger(
        user_id=user_id,
        session_id=None,
        log_type=log_type,
        log_level=log_level,
        console_output_files=console_output_files
    )

def setup_logger(
    user_id: str, 
    session_id: int, 
    log_level: int = logging.INFO,
    console_output_files: Optional[List[str]] = None
) -> SessionLogger:
    """Setup a new session logger.
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        log_level: Logging level (default: logging.INFO)
        console_output_files: List of file names to output to console
    """
    return SessionLogger(
        user_id=user_id,
        session_id=session_id,
        log_level=log_level,
        console_output_files=console_output_files
    )
