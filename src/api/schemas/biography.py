from typing import Dict
from pydantic import BaseModel

class EditData(BaseModel):
    newTitle: str | None = None
    newContent: str | None = None
    newPath: str | None = None
    sectionPrompt: str | None = None
    comment: Dict[str, str] | None = None

class BiographyEdit(BaseModel):
    type: str  # 'RENAME' | 'DELETE' | 'CONTENT_CHANGE' | 'COMMENT' | 'ADD'
    sectionId: str
    title: str
    data: EditData | None = None
    timestamp: int