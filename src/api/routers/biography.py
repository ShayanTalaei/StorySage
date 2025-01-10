import os
import json
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from api.core.auth import get_current_user

router = APIRouter(
    tags=["biography"]
)

def get_latest_biography(user_id: str) -> Dict[Any, Any]:
    """Helper function to get the latest biography version for a user"""
    data_dir = os.getenv('DATA_DIR')
    if not data_dir:
        raise HTTPException(
            status_code=500,
            detail="DATA_DIR environment variable not set"
        )
    
    user_dir = os.path.join(data_dir, user_id)
    
    # Check if user directory exists
    if not os.path.exists(user_dir):
        return None
    
    # Find all biography files for the user
    bio_files = [f for f in os.listdir(user_dir) if f.startswith('biography_') and f.endswith('.json')]
    
    if not bio_files:
        return None
    
    # Extract version numbers and find the highest one
    versions = [int(f.split('_')[1].split('.')[0]) for f in bio_files]
    latest_version = max(versions)
    latest_file = f'biography_{latest_version}.json'
    
    # Read and return the latest biography
    try:
        with open(os.path.join(user_dir, latest_file), 'r') as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading biography file: {str(e)}"
        )

@router.get("/biography/latest")
async def get_user_biography(
    current_user: str = Depends(get_current_user)
) -> Dict[Any, Any]:
    """Get the latest biography for the current user"""
    biography = get_latest_biography(current_user)
    
    if biography is None:
        raise HTTPException(
            status_code=404,
            detail="No biography found for user"
        )
    
    return biography
