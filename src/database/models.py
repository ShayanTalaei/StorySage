from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class DBSession(Base):
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    messages = relationship("DBMessage", back_populates="session")

class DBMessage(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    content = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "User" or "Interviewer"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("DBSession", back_populates="messages") 