from dataclasses import dataclass
from typing import Optional, List

@dataclass
class TodoItem:
    section_path: str
    update_plan: str
    relevant_memories: List[str]  # List of memory texts
    action_type: str = "update"  # "update" or "create"
    section_title: Optional[str] = None  # Only needed for "create" action
    status: str = "pending"