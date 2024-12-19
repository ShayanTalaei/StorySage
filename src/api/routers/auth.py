from fastapi import APIRouter
from api.schemas.auth import LoginRequest, TokenResponse
from api.auth import create_access_token

router = APIRouter(tags=["auth"])

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login to get access token.
    For now, just use user_id as user_id without any verification."""
    user_id = request.user_id
    access_token = create_access_token(
        data={"sub": user_id}
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    ) 