from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class TodoItem:
    section_path: str
    update_plan: str
    action_type: str = "update"  # "update" or "create"
    section_title: Optional[str] = None  # Only needed for "create" action
    status: str = "pending"