from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import asyncio
import uuid
import time
from pathlib import Path
import os

from api.schemas.chat import (
    MessageRequest, MessageResponse, EndSessionResponse, UserMessagesResponse, TopicsResponse, TopicsFeedbackRequest
)
from database.models import DBSession, DBMessage
from database.database import get_db
from interview_session.interview_session import InterviewSession
from api.core.auth import get_current_user
from api.core.session_manager import session_manager
from interview_session.session_models import MessageType
from utils.constants.colors import RESET, RED

router = APIRouter(
    tags=["chat"]
)


async def check_inactive_sessions():
    while True:
        try:
            # Get inactive users
            inactive_users = session_manager.check_inactive_sessions()
            
            # End sessions for inactive users
            for user_id in inactive_users:
                session = session_manager.get_active_session(user_id)
                if session:
                    print(f"{RED}Ending inactive session for user: {user_id}{RESET}")
                    session.end_session()
                    
                    # Wait up to 30 seconds for session to complete its final tasks
                    cleanup_timeout_seconds = session.timeout_minutes * 60
                    start_time = time.time()
                    while not session.session_completed:
                        await asyncio.sleep(0.1)
                        if time.time() - start_time > cleanup_timeout_seconds:
                            print(f"{RED}Timeout waiting for session cleanup for user: {user_id}{RESET}")
                            break
                            
                    session_manager.end_session(user_id)
                    
        except Exception as e:
            print(f"{RED}Error in check_inactive_sessions:\n{e}\n{RESET}")
            
        await asyncio.sleep(180)  # Check every 3 minutes

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
            
            # Start the inactive session checker if it's not already running
            asyncio.create_task(check_inactive_sessions())
        else:
            session_id = session.get_db_session_id()
        
        # Update last activity time
        session_manager.update_last_activity(current_user)
        
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

@router.post("/skip", response_model=MessageResponse)
async def skip_message(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Send a skip signal to the active session"""
    try:
        session = session_manager.get_active_session(current_user)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="No active session found"
            )

        session_id = session.get_db_session_id()
        
        # Update last activity time
        session_manager.update_last_activity(current_user)
        
        # Add skip signal to interview session
        session.add_message_to_chat_history("User", message_type=MessageType.SKIP)

        # Store skip action in database
        user_skip_message = DBMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            content="[Skip]",
            role="Feedback"
        )
        db.add(user_skip_message)
        db.commit()
        
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
        if session:
            session_manager.end_session(current_user)
        print(f"{RED}Error:\n{e}\n{RESET}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/like", response_model=MessageResponse)
async def like_message(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Send a like signal to the active session"""
    try:
        session = session_manager.get_active_session(current_user)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="No active session found"
            )

        session_id = session.get_db_session_id()
        
        # Update last activity time
        session_manager.update_last_activity(current_user)
        
        # Add like signal to interview session
        session.add_message_to_chat_history("User", message_type=MessageType.LIKE)
        
        # Store like action in database
        response_id = str(uuid.uuid4())
        db_response = DBMessage(
            id=response_id,
            session_id=session_id,
            content="[Like]",
            role="Feedback"
        )
        db.add(db_response)
        db.commit()
        
        return MessageResponse(
            id=response_id,
            content="[Like]",
            role="User",
            created_at=db_response.created_at
        )
    except Exception as e:
        db.rollback()
        if session:
            session_manager.end_session(current_user)
        print(f"{RED}Error:\n{e}\n{RESET}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/prepare-end", response_model=TopicsResponse)
async def prepare_end_session(
    current_user: str = Depends(get_current_user)
):
    """First stage of ending session - get topics covered"""
    try:
        if not session_manager.has_active_session(current_user):
            raise HTTPException(
                status_code=404,
                detail="No active session found"
            )
        
        # Get the active session
        session = session_manager.get_active_session(current_user)

        # Wait for note taker to finish processing
        while session.note_taker.processing_in_progress:
            await asyncio.sleep(0.1)
        
        # Start biography update in background
        asyncio.create_task(session.biography_orchestrator.update_biography())
        
        # Get topics from new memories
        topics = await session.biography_orchestrator.get_session_topics()
        
        return TopicsResponse(
            topics=topics,
            status="success"
        )
        
    except Exception as e:
        print(f"{RED}Error:\n{e}\n{RESET}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/end", response_model=EndSessionResponse)
async def end_session(
    feedback: TopicsFeedbackRequest,
    current_user: str = Depends(get_current_user)
):
    """End the active session with user's topic feedback"""
    try:
        if not session_manager.has_active_session(current_user):
            raise HTTPException(
                status_code=404,
                detail="No active session found"
            )
        
        # Get the active session
        session = session_manager.get_active_session(current_user)
        
        # Set selected topics to unblock session note update
        await session.biography_orchestrator.set_selected_topics(feedback.selected_topics)
        
        # Store general session feedback if provided
        if feedback.feedback:
            # Create feedback directory if it doesn't exist
            logs_dir = Path(os.getenv("LOGS_DIR", "logs"))
            feedback_dir = logs_dir / current_user / "feedback"
            feedback_dir.mkdir(parents=True, exist_ok=True)
            
            # Get session sequence ID
            session_id = session.session_id
            
            # Write feedback to file
            feedback_file = feedback_dir / f"session_{session_id}.txt"
            feedback_content = (
                f"Session Rating: {feedback.feedback.rating}\n"
                f"Detailed Feedback:\n{feedback.feedback.feedback}\n"
            )
            
            with open(feedback_file, "w", encoding="utf-8") as f:
                f.write(feedback_content)
        
        # End session without triggering another biography update
        session.end_session()
        
        # Wait for completion with timeout
        start_time = time.time()
        while not session.session_completed:
            await asyncio.sleep(0.1)
            if time.time() - start_time > 300: # 5 minutes timeout
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

@router.get("/messages", response_model=UserMessagesResponse)
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
        db_messages = (
            db.query(DBMessage)
            .filter(DBMessage.session_id.in_(session_ids))
            .order_by(DBMessage.created_at)
            .all()
        )
        
        # Convert DB messages to MessageResponse objects
        messages = [
            MessageResponse(
                id=msg.id,
                content=msg.content,
                role=msg.role,
                created_at=msg.created_at
            ) 
            for msg in db_messages
        ]
        
        # Check if user has an active session
        has_active_session = session_manager.has_active_session(current_user)
        
        return UserMessagesResponse(
            messages=messages,
            has_active_session=has_active_session
        )
        
    except Exception as e:
        print(f"{RED}Error:\n{e}\n{RESET}")
        raise HTTPException(status_code=500, detail=str(e))
