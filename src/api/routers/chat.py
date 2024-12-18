from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import asyncio
import uuid

from api.schemas import (
    SessionRequest, MessageRequest, SessionResponse, MessageResponse
)
from database.models import DBSession, DBMessage
from database.database import get_db
from interview_session.interview_session import InterviewSession

router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

# Store active sessions
active_sessions = {}

@router.post("/sessions", response_model=SessionResponse)
async def create_session(request: SessionRequest, db: Session = Depends(get_db)):
    try:
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
async def send_message(request: MessageRequest, db: Session = Depends(get_db)):
    try:
        session = active_sessions.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
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
