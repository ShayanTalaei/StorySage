from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import asyncio
import uuid
from typing import List

from api.schemas.chat import (
    SessionRequest, MessageRequest, SessionResponse, MessageResponse, EndSessionResponse, MessageResponse
)
from database.models import DBSession, DBMessage
from database.database import get_db
from interview_session.interview_session import InterviewSession
from api.auth import get_current_user

router = APIRouter(
    tags=["chat"]
)

# Store active sessions
active_sessions = {}

@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: SessionRequest, 
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Create a new interview session"""
    try:
        # Verify the user is creating a session for themselves
        if request.user_id != current_user:
            raise HTTPException(
                status_code=403, 
                detail="Cannot access another user's session"
            )
        # Create a new interview session
        session = InterviewSession(
            user_id=request.user_id,
            interaction_mode='api',
            enable_voice_output=False,
            enable_voice_input=False
        )
        
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        active_sessions[session_id] = session
        
        # Create database session record
        db_session = DBSession(
            id=session_id,
            user_id=request.user_id
        )
        db.add(db_session)
        
        # Start the session in the background
        asyncio.create_task(session.run())
        
        # If initial content is provided, send it
        if request.content:
            session.add_message_to_chat_history("User", request.content)
            
            # Store user message in database
            db_message = DBMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                content=request.content,
                role="User"
            )
            db.add(db_message)
            
            # Wait for interviewer's response
            response = await session.api_participant.wait_for_response()
            if not response:
                raise HTTPException(status_code=408, detail="Timeout waiting for interviewer response")
            
            # Store interviewer response in database
            db_response = DBMessage(
                id=response.id,
                session_id=session_id,
                content=response.content,
                role="Interviewer",
                created_at=response.timestamp
            )
            db.add(db_response)
            db.commit()
            
            last_message = response
        else:
            raise HTTPException(status_code=400, detail="The message is empty.")

        return SessionResponse(
            session_id=session_id,
            message=MessageResponse(
                message_id=last_message.id,
                content=last_message.content,
                created_at=last_message.timestamp,
                role=last_message.role
            )
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/messages", response_model=MessageResponse)
async def send_message(
    request: MessageRequest, 
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Send a message to the interview session"""
    try:
        session: InterviewSession = active_sessions.get(request.session_id, None)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        # Verify the session belongs to the current user
        if session.user_id != current_user:
            raise HTTPException(
                status_code=403, 
                detail="Cannot access another user's session"
            )
        
        # Store user message in database
        db_message = DBMessage(
            id=str(uuid.uuid4()),
            session_id=request.session_id,
            content=request.content,
            role="User"
        )
        db.add(db_message)
        
        # Add user message to chat history
        session.add_message_to_chat_history("User", request.content)
        
        # Wait for interviewer's response
        response = await session.api_participant.wait_for_response()
        if not response:
            raise HTTPException(status_code=408, detail="Timeout waiting for interviewer response")
        
        # Store interviewer response in database
        db_response = DBMessage(
            id=response.id,
            session_id=request.session_id,
            content=response.content,
            role="Interviewer",
            created_at=response.timestamp
        )
        db.add(db_response)
        db.commit()
        
        return MessageResponse(
            message_id=response.id,
            content=response.content,
            created_at=response.timestamp,
            role=response.role
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/{session_id}/end", response_model=EndSessionResponse)
async def end_session(session_id: str, db: Session = Depends(get_db)):
    """End an interview session and update biography"""
    try:
        session: InterviewSession = active_sessions.get(session_id, None)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found. Check the session ID.")
        
        # End the session - this will trigger biography update in the run() method
        session.session_in_progress = False
        
        # Remove from active sessions
        active_sessions.pop(session_id, None)
        
        return EndSessionResponse(
            status="success",
            message="Session ended successfully",
            session_id=session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def list_session_messages(session_id: str, db: Session = Depends(get_db)):
    """Retrieve all messages for a specific session"""
    try:
        # Check if session exists
        session: InterviewSession = active_sessions.get(session_id, None)
        if not session:
            # If session is not active, check if it exists in database
            db_session = db.query(DBSession).filter(DBSession.id == session_id).first()
            if not db_session:
                raise HTTPException(
                    status_code=404, 
                    detail="Session not found. Check the session ID."
                )
        
        # Query messages from database
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

