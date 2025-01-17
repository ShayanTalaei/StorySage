from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import asyncio
import uuid
import time

from api.schemas.chat import (
    MessageRequest, MessageResponse, EndSessionResponse
)
from database.models import DBSession, DBMessage
from database.database import get_db
from interview_session.interview_session import InterviewSession
from api.core.auth import get_current_user
from api.core.session_manager import session_manager

router = APIRouter(
    tags=["chat"]
)

# Console colors
GREEN = '\033[92m'
RESET = '\033[0m'
RED = '\033[91m'

@router.post("/messages", response_model=MessageResponse)
async def send_message(
    request: MessageRequest, 
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Send a message to the active session or create a new one"""
    try:
        session = session_manager.get_active_session(current_user)
        session_id = None

        # Get session ID
        if not session:
            # Create a new session if none exists
            session = InterviewSession(
                interaction_mode='api',
                user_config={
                    "user_id": current_user
                }
            )
            
            # Get sequence ID from interview session
            seq_id = session.session_id
            session_id = str(uuid.uuid4())
            
            # Create database session record
            db_session = DBSession(
                id=session_id,
                seq_id=seq_id,
                user_id=current_user
            )
            db.add(db_session)

            # Sync database session ID with interview session
            session.set_db_session_id(session_id)
            
            # Start session in the background
            asyncio.create_task(session.run())
            
            # Store session in manager after initialization
            session_manager.set_active_session(current_user, session) 
        else:
            session_id = session.get_db_session_id()
        
        # Store user message
        db_message = DBMessage(
            id=str(uuid.uuid4()),
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
        response_id = str(uuid.uuid4())
        db_response = DBMessage(
            id=response_id,
            session_id=session_id,
            content=response.content,
            role="Interviewer"
        )
        db.add(db_response)
        db.commit()
        
        return MessageResponse(
            id=response_id,
            content=response.content,
            role=response.role,
            created_at=db_response.created_at
        )
    except Exception as e:
        db.rollback()
        if session:  # Clean up session on error
            session_manager.end_session(current_user)
        print(f"{RED}Error:\n{e}\n{RESET}")
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
        
        # Get the active session
        session = session_manager.get_active_session(current_user)
        
        # Set session_in_progress to False to trigger completion
        session.session_in_progress = False
        
        # Wait for the session to complete its final tasks
        timeout = 120
        start_time = time.time()
        
        while not session.session_completed:
            await asyncio.sleep(0.1)
            if time.time() - start_time > timeout:
                raise HTTPException(
                    status_code=408,
                    detail="Timeout waiting for session to complete."
                )
        
        # Clean up the session
        session_manager.end_session(current_user)
        
        return EndSessionResponse(
            status="success",
            message="Session ended successfully"
        )
        
    except Exception as e:
        print(f"{RED}Error:\n{e}\n{RESET}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{seq_id}/messages", response_model=List[MessageResponse])
async def list_session_messages(
    seq_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Retrieve all messages for a specific session (active or not)"""
    try:
        db_session = db.query(DBSession).filter(
            DBSession.seq_id == seq_id,
            DBSession.user_id == current_user
        ).first()

        if not db_session:
            raise HTTPException(
                status_code=404, 
                detail="Session not found."
            )
        
        messages = (
            db.query(DBMessage)
            .filter(DBMessage.session_id == db_session.id)
            .order_by(DBMessage.created_at)
            .all()
        )
        
        return messages
        
    except Exception as e:
        print(f"{RED}Error:\n{e}\n{RESET}")
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
        print(f"{RED}Error:\n{e}\n{RESET}")
        raise HTTPException(status_code=500, detail=str(e))
