from pydantic import BaseModel
from datetime import datetime
from typing import List

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

class UserMessagesResponse(BaseModel):
    messages: List[MessageResponse]
    has_active_session: bool

class TopicsResponse(BaseModel):
    topics: List[str]
    status: str

class TopicsFeedbackRequest(BaseModel):
    selected_topics: List[str]