import os
import json
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

from api.core.auth import get_current_user
from api.schemas.biography import BiographyEdit
from content.biography.biography import Biography
from agents.biography_team.orchestrator import BiographyOrchestrator
from agents.biography_team.base_biography_agent import BiographyConfig

router = APIRouter(
    tags=["biography"],
    prefix="/biography"
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

@router.get("/latest")
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

@router.post("/edit")
async def edit_biography(
    edits: List[BiographyEdit],
    current_user: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """Apply a list of edits to the user's biography"""
    
    # Load the latest biography
    bio = Biography.load_from_file(current_user)
    
    # Separate AI-powered edits from basic edits
    ai_edits: List[BiographyEdit] = []
    basic_edits: List[BiographyEdit] = []
    
    for edit in edits:
        if edit.type in ["ADD", "COMMENT"]:
            ai_edits.append(edit)
        else:
            basic_edits.append(edit)
    
    # Process basic edits first
    for edit in sorted(basic_edits, key=lambda x: x.timestamp):
        try:
            if edit.type == "RENAME":
                if not edit.data or not edit.data.newTitle:
                    raise ValueError("New title is required for RENAME operation")
                bio.update_section(title=edit.title, new_title=edit.data.newTitle)
                
            elif edit.type == "DELETE":
                if not bio.delete_section(title=edit.title):
                    raise ValueError(f"Section not found: {edit.title}")
                
            elif edit.type == "CONTENT_CHANGE":
                if not edit.data or not edit.data.newContent:
                    raise ValueError("New content is required for CONTENT_CHANGE operation")
                bio.update_section(title=edit.title, content=edit.data.newContent)
                
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error processing edit {edit.type} for section '{edit.title}': {str(e)}"
            )
    
    # Save changes from basic edits
    if basic_edits:
        bio.save()
    
    # Process AI-powered edits if any exist
    if ai_edits:
        # Create orchestrator instance for AI-powered edits
        config = BiographyConfig(user_id=current_user)
        orchestrator = BiographyOrchestrator(config=config, interview_session=None)
        
        # Convert edits to dict format expected by orchestrator
        edit_dicts = [edit.dict() for edit in ai_edits]
        
        # Process edits through the orchestrator
        try:
            await orchestrator.process_user_edits(edit_dicts)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error processing AI edits: {str(e)}"
            )
    
    # Return the latest saved biography
    latest_bio = get_latest_biography(current_user)
    if latest_bio is None:
        raise HTTPException(
            status_code=404,
            detail="Failed to retrieve updated biography"
        )
    
    return latest_bio
