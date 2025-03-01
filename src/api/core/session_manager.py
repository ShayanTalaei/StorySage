from typing import Dict, Optional, Set
from interview_session.interview_session import InterviewSession
import time

class SessionManager:
    """Manages active interview sessions for users"""
    
    def __init__(self):
        # Map of user_id to their active session
        self._active_sessions: Dict[str, InterviewSession] = {}
        self._ending_sessions: Set[str] = set()  # Track sessions that are ending
    
    def get_active_session(self, user_id: str) -> Optional[InterviewSession]:
        """Get active session for a user"""
        return self._active_sessions.get(user_id)
    
    def set_active_session(self, user_id: str, session: InterviewSession):
        """Set active session for a user"""
        # End any existing session first
        if user_id in self._active_sessions:
            self.end_session(user_id)
        self._active_sessions[user_id] = session
        
        # Remove from ending sessions if it was there
        if user_id in self._ending_sessions:
            self._ending_sessions.remove(user_id)
    
    def end_session(self, user_id: str):
        """End active session for a user"""
        if user_id in self._active_sessions:
            session = self._active_sessions[user_id]
            session.end_session()
            del self._active_sessions[user_id]
            if user_id in self._ending_sessions:
                self._ending_sessions.remove(user_id)
    
    def mark_session_ending(self, user_id: str):
        """Mark a session as ending but don't remove it yet"""
        if user_id in self._active_sessions:
            self._ending_sessions.add(user_id)
    
    def has_active_session(self, user_id: str) -> bool:
        """Check if user has an active session"""
        return user_id in self._active_sessions

    def check_inactive_sessions(self, timeout_minutes: int = 10):
        """Check for inactive sessions and sessions that have completed"""
        to_remove = []
        
        # Check all active sessions
        for user_id, session in self._active_sessions.items():
            # Check if session has completed its processing
            if session.session_completed:
                to_remove.append(user_id)
                continue
        
        # Remove sessions
        for user_id in to_remove:
            if user_id in self._active_sessions:
                self.end_session(user_id)
        
        return to_remove

    def has_ending_session(self, user_id: str) -> bool:
        """Check if user has a session that's in the ending state"""
        return user_id in self._ending_sessions

# Global session manager instance
session_manager = SessionManager() 