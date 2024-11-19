import logging
import pathlib
from datetime import datetime
import os
from typing import List
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
    
    @classmethod
    def log_to_file(cls, file_name: str, message: str, log_level: str = "info") -> None:
        """
        Logs a message to a specific file within the session's execution_logs directory.
        
        Args:
            file_name: Name of the log file (without .log extension)
            message: Message to log
        """
        # Get the current instance's user_id and session_id from thread local storage
        current_logger = cls.get_current_logger()
        if not current_logger:
            raise RuntimeError("No logger has been initialized. Call setup_logger first.")
            
        # Create logger for this specific file
        file_logger = logging.getLogger(f"{current_logger.user_id}_{current_logger.session_id}_{file_name}")
        
        # Define log_file path before the handlers check
        log_file = current_logger.log_dir / f"{file_name}.log"
        
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
        with cls._locks_lock:
            file_lock = cls._file_locks.get(log_file)
            if file_lock is None:
                file_lock = threading.Lock()
                cls._file_locks[log_file] = file_lock
        
        # Use the lock when writing to file
        with file_lock:
            file_logger.log(LOG_LEVELS[log_level]["log_level"], message)

    _current_logger = None

    @classmethod
    def get_current_logger(cls):
        return cls._current_logger

    def __init__(self, user_id: str, session_id: int, log_level=logging.INFO, console_output_files: List[str] = None):
        self.user_id = user_id
        self.session_id = session_id
        self.log_level = log_level
        self.console_output_files = console_output_files
        
        # Store this instance as the current logger
        SessionLogger._current_logger = self
        
        # Setup base logger
        self.logger = logging.getLogger(f"session_{user_id}_{session_id}")
        
        if not self.logger.handlers:
            self.logger.setLevel(log_level)
            
            # Base log directory
            self.log_dir = pathlib.Path(LOGS_DIR) / user_id / "execution_logs" / f"session_{session_id}"
            self.log_dir.mkdir(parents=True, exist_ok=True)
            
            if self.console_output_files:
                console_handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)
    
def setup_logger(user_id: str, session_id: int, log_level=logging.INFO, console_output_files: List[str] = None) -> SessionLogger:
    return SessionLogger(user_id, session_id, log_level, console_output_files) 
