from typing import Dict, Optional
from interview_session.interview_session import InterviewSession
import time

class SessionManager:
    """Manages active interview sessions for users"""
    
    def __init__(self):
        # Map of user_id to their active session
        self._active_sessions: Dict[str, InterviewSession] = {}
        self.last_activity = {}  # Track last activity time for each user
    
    def get_active_session(self, user_id: str) -> Optional[InterviewSession]:
        """Get active session for a user"""
        return self._active_sessions.get(user_id)
    
    def set_active_session(self, user_id: str, session: InterviewSession):
        """Set active session for a user"""
        # End any existing session first
        if user_id in self._active_sessions:
            self.end_session(user_id)
        self._active_sessions[user_id] = session
        self.last_activity[user_id] = time.time()
    
    def end_session(self, user_id: str):
        """End active session for a user"""
        if user_id in self._active_sessions:
            session = self._active_sessions[user_id]
            session.session_in_progress = False
            del self._active_sessions[user_id]
            del self.last_activity[user_id]
    
    def has_active_session(self, user_id: str) -> bool:
        """Check if user has an active session"""
        return user_id in self._active_sessions

    def update_last_activity(self, user_id: str):
        if user_id in self.last_activity:
            self.last_activity[user_id] = time.time()

    def check_inactive_sessions(self, timeout_minutes: int = 10):
        current_time = time.time()
        inactive_users = []
        
        for user_id, last_active in self.last_activity.items():
            if current_time - last_active > timeout_minutes * 60:
                inactive_users.append(user_id)
        
        return inactive_users

# Global session manager instance
session_manager = SessionManager() 