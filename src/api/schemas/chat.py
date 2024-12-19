from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MessageResponse(BaseModel):
    id: str
    content: str
    created_at: datetime
    role: str

    class Config:
        orm_mode = True

class SessionRequest(BaseModel):
    user_id: str
    content: Optional[str] = None

class MessageRequest(BaseModel):
    session_id: str
    content: str

class SessionResponse(BaseModel):
    session_id: str
    message: MessageResponse

    class Config:
        orm_mode = True

class EndSessionResponse(BaseModel):
    status: str
    message: str
    session_id: str