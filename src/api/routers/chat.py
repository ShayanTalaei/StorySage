from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import asyncio
import uuid

from api.schemas.chat import (
    MessageRequest, MessageResponse, EndSessionResponse
)
from database.models import DBSession, DBMessage
from database.database import get_db
from interview_session.interview_session import InterviewSession
from api.auth import get_current_user
from api.session_manager import session_manager

router = APIRouter(
    tags=["chat"]
)

@router.post("/messages", response_model=MessageResponse)
async def send_message(
    request: MessageRequest, 
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Send a message to the active session or create a new one"""
    try:
        session = session_manager.get_active_session(current_user)
        
        # Get session ID
        if not session:
            # Create a new session if none exists
            session = InterviewSession(
                user_id=current_user,
                interaction_mode='api',
                enable_voice_output=False,
                enable_voice_input=False
            )
            
            # Get session ID before starting the session
            session_id = session.session_id
            
            # Create database session record
            db_session = DBSession(
                id=session_id,
                user_id=current_user
            )
            db.add(db_session)
            
            # Start session in the background
            asyncio.create_task(session.run())
            
            # Store session in manager after initialization
            session_manager.set_active_session(current_user, session)
        else:
            session_id = session.session_id
        
        # Store user message
        db_message = DBMessage(
            id=str(uuid.uuid4()),  # Message IDs can still be UUIDs
            session_id=session_id,
            content=request.content,
            role="User"
        )
        db.add(db_message)
        
        # Add user message to interview session
        session.add_message_to_chat_history("User", request.content)
        
        # Get response
        response = await session.api_participant.wait_for_response()
        if not response:
            raise HTTPException(status_code=408, detail="Timeout waiting for interviewer response")
        
        # Store interviewer response
        db_response = DBMessage(
            id=response.id,
            session_id=session_id,
            content=response.content,
            role="Interviewer"
        )
        db.add(db_response)
        db.commit()
        
        return MessageResponse(
            id=response.id,
            content=response.content,
            role=response.role,
            created_at=db_response.created_at
        )
    except Exception as e:
        db.rollback()
        if session:  # Clean up session on error
            session_manager.end_session(current_user)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/end", response_model=EndSessionResponse)
async def end_session(
    current_user: str = Depends(get_current_user)
):
    """End the active session"""
    try:
        if not session_manager.has_active_session(current_user):
            raise HTTPException(
                status_code=404,
                detail="No active session found"
            )
        
        session_manager.end_session(current_user)
        
        return EndSessionResponse(
            status="success",
            message="Session ended successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def list_session_messages(session_id: str, db: Session = Depends(get_db)):
    """Retrieve all messages for a specific session (active or not)"""
    try:
        db_session = db.query(DBSession).filter(DBSession.id == session_id).first()
        if not db_session:
            raise HTTPException(
                status_code=404, 
                detail="Session not found."
            )
        
        messages = (
            db.query(DBMessage)
            .filter(DBMessage.session_id == session_id)
            .order_by(DBMessage.created_at)
            .all()
        )
        
        return messages
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/messages", response_model=List[MessageResponse])
async def list_user_messages(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Retrieve all messages for the current user"""
    try:
        # Get all sessions for this user
        sessions = (
            db.query(DBSession)
            .filter(DBSession.user_id == current_user)
            .all()
        )
        
        # Get all messages from these sessions
        session_ids = [session.id for session in sessions]
        messages = (
            db.query(DBMessage)
            .filter(DBMessage.session_id.in_(session_ids))
            .order_by(DBMessage.created_at)
            .all()
        )
        
        return messages
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))