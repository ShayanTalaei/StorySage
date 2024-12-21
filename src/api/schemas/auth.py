from pydantic import BaseModel

class LoginRequest(BaseModel):
    """Request model for user login"""
    user_id: str
    password: str

class TokenResponse(BaseModel):
    """Response model for successful login"""
    access_token: str
    token_type: str = "bearer"
