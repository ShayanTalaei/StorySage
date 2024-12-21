from pydantic import BaseModel
from datetime import datetime

class MessageResponse(BaseModel):
    id: str
    content: str
    created_at: datetime
    role: str

    class Config:
        orm_mode = True

class MessageRequest(BaseModel):
    content: str

class EndSessionResponse(BaseModel):
    status: str
    message: str