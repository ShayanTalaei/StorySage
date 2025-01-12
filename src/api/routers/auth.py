from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from database.database import get_db
from database.models import DBUser
from api.schemas.auth import LoginRequest, TokenResponse
from api.core.auth import create_access_token

router = APIRouter(tags=["auth"])

# Password hashing - use same context as register
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/user/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login to get access token"""
    # Get user from database
    user = db.query(DBUser).filter(DBUser.user_id == request.user_id).first()
    
    # Verify user exists and password matches
    if not user or not pwd_context.verify(request.password, user.password_hash):
        print("Hello")
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password."
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.user_id}
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )

## create user file