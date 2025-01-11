from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy

Base = declarative_base()

class DBSession(Base):
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True)
    seq_id = Column(Integer, nullable=False)
    user_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    messages = relationship("DBMessage", back_populates="session")
    # user = relationship("DBUser")
    
    # TODO: Disabled for development; uncomment for production
    # __table_args__ = (
    #     sqlalchemy.UniqueConstraint('user_id', 'seq_id', name='unique_user_session_seq'),
    # )

class DBMessage(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    content = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "User" or "Interviewer"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("DBSession", back_populates="messages") 

class DBUser(Base):
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow) 