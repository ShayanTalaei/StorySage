from pydantic import BaseModel
from datetime import datetime

class StatusResponse(BaseModel):
    """Base response model for status messages"""
    status: str
    message: str

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "Operation completed successfully"
            }
        } 