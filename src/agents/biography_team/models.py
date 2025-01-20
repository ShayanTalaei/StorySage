from dataclasses import dataclass
from typing import List, Optional

@dataclass
class TodoItem:
    update_plan: str
    relevant_memories: str
    status: str = "pending"
    action_type: str = "update"  # "update" or "create"
    section_path: Optional[str] = None  # Path-based section identifier
    section_title: Optional[str] = None  # Title-based section identifier
    error: Optional[str] = None  # For storing error messages if status is "failed"

    def __post_init__(self):
        # Ensure at least one section identifier is provided
        if not self.section_path and not self.section_title:
            raise ValueError("Either section_path or section_title must be provided")