from pydantic import BaseModel

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