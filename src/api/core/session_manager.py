from typing import Dict, Optional, Set
from api.schemas.chat import SessionStatus
from interview_session.interview_session import InterviewSession

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
        """Mark a session as ending but don't remove it yet
           Writing subsequent session notes still in progress"""
        if user_id in self._active_sessions:
            self._ending_sessions.add(user_id)

    def remove_inactive_sessions(self):
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
    
    def get_session_status(self, user_id: str) -> str:
        """Get the current session status for a user
        
        Returns:
            str: "active" if user has an active session that's not ending
                 "ending" if user has an active session that's in the ending state
                 "inactive" if user has no active session
        """
        if not user_id in self._active_sessions:
            return SessionStatus.INACTIVE
        
        if user_id in self._ending_sessions:
            return SessionStatus.ENDING
        
        return SessionStatus.ACTIVE

# Global session manager instance
session_manager = SessionManager() 