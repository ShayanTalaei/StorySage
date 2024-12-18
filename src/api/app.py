from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
import asyncio
from typing import Dict
import uuid
import os
from pathlib import Path

from api.schemas import (
    SessionRequest, MessageRequest, SessionResponse, MessageResponse
)
from database.models import DBSession, DBMessage
from database.database import get_db, SQLALCHEMY_DATABASE_URL
from interview_session.interview_session import InterviewSession

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Check if database exists on startup"""
    if SQLALCHEMY_DATABASE_URL.startswith('sqlite:///'):
        db_path = SQLALCHEMY_DATABASE_URL.replace('sqlite:///', '')
        if not os.path.exists(db_path):
            raise Exception(
                "Database not found! Please run 'python src/database/setup_db.py' "
                "to initialize the database."
            )

# Store active sessions
active_sessions: Dict[str, InterviewSession] = {}

@app.post("/sessions", response_model=SessionResponse)
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

@app.post("/messages", response_model=MessageResponse)
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

# Optional: Add session cleanup endpoint
@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    if session_id in active_sessions:
        session = active_sessions[session_id]
        session.session_in_progress = False
        del active_sessions[session_id]
        return {"status": "success", "message": "Session deleted"}
    raise HTTPException(status_code=404, detail="Session not found") 