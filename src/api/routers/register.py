from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from database.database import get_db
from database.models import DBUser
from api.schemas.auth import RegisterRequest, RegisterResponse
from api.core.auth import create_access_token

router = APIRouter(tags=["register"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/user/register", response_model=RegisterResponse)
async def register_user(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        # Check if user already exists
        existing_user = db.query(DBUser).filter(DBUser.user_id == request.user_id).first()
        if existing_user:
            # raise HTTPException(
            #     status_code=400,
            #     detail="User ID already registered"
            # )

            print(f"Attempted registration with existing user_id: {request.user_id}")  # Added print statement

            raise HTTPException(
                status_code=400,
                detail="User ID already registered. Please login instead."
            )
            
        
        # Hash the password
        hashed_password = pwd_context.hash(request.password)
        
        # Create new user
        new_user = DBUser(
            user_id=request.user_id,
            password_hash=hashed_password
        )
        
        # Add to database
        db.add(new_user)
        db.commit()
        
        # Generate access token
        access_token = create_access_token(data={"sub": request.user_id})
        
        return RegisterResponse(
            message="User registered successfully",
            user_id=request.user_id,
            access_token=access_token
        )
        
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
