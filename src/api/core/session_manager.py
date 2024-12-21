from typing import Dict, Optional
from interview_session.interview_session import InterviewSession

class SessionManager:
    """Manages active interview sessions for users"""
    
    def __init__(self):
        # Map of user_id to their active session
        self._active_sessions: Dict[str, InterviewSession] = {}
    
    def get_active_session(self, user_id: str) -> Optional[InterviewSession]:
        """Get active session for a user"""
        return self._active_sessions.get(user_id)
    
    def set_active_session(self, user_id: str, session: InterviewSession):
        """Set active session for a user"""
        # End any existing session first
        if user_id in self._active_sessions:
            self.end_session(user_id)
        self._active_sessions[user_id] = session
    
    def end_session(self, user_id: str):
        """End active session for a user"""
        if user_id in self._active_sessions:
            session = self._active_sessions[user_id]
            session.session_in_progress = False
            del self._active_sessions[user_id]
    
    def has_active_session(self, user_id: str) -> bool:
        """Check if user has an active session"""
        return user_id in self._active_sessions

# Global session manager instance
session_manager = SessionManager() 