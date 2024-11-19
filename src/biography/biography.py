from datetime import datetime
import json
from typing import Dict, Optional, List
import uuid
import os

class Section:
    def __init__(self, title: str, content: str = "", parent: Optional['Section'] = None):
        self.id = str(uuid.uuid4())
        self.title = title
        self.content = content
        self.created_at = datetime.now().isoformat()
        self.last_edit = datetime.now().isoformat()
        self.parent = parent
        self.subsections: Dict[str, 'Section'] = {}

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "created_at": self.created_at,
            "last_edit": self.last_edit,
            "subsections": {k: v.to_dict() for k, v in self.subsections.items()}
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Section':
        section = cls(data["title"])
        section.id = data["id"]
        section.content = data["content"]
        section.created_at = data["created_at"]
        section.last_edit = data["last_edit"]
        section.subsections = {k: cls.from_dict(v) for k, v in data["subsections"].items()}
        return section

class Biography:
    def __init__(self, user_id):
        self.user_id = user_id or str(uuid.uuid4())
        self.base_path = f"data/{self.user_id}/"
        os.makedirs(self.base_path, exist_ok=True)
        self.file_path = f"{self.base_path}/biography.json"
        self.root = Section(f"Biography of {self.user_id}")

    @classmethod
    def load_from_file(cls, user_id: str) -> 'Biography':
        """Load a biography from file or create new one if it doesn't exist."""
        biography = cls(user_id)
        try:
            with open(biography.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                biography.root = Section.from_dict(data)
        except FileNotFoundError:
            pass  # Use the default empty biography if file doesn't exist
        return biography

    def get_section_by_path(self, path: str) -> Optional[Section]:
        """Get a section using its path (e.g., 'Chapter 1/Section 1.1')"""
        if not path:
            return self.root

        current = self.root
        for part in path.split('/'):
            if part in current.subsections:
                current = current.subsections[part]
            else:
                return None
        return current

    def get_section_by_title(self, title: str) -> Optional[Section]:
        """Find a section by its title using DFS"""
        def _search(section: Section) -> Optional[Section]:
            if section.title == title:
                return section
            for subsection in section.subsections.values():
                result = _search(subsection)
                if result:
                    return result
            return None
        
        return _search(self.root)

    def add_section(self, path: str, title: str, content: str = "") -> Section:
        """Add a new section at the specified path"""
        parent_path = '/'.join(path.split('/')[:-1]) if '/' in path else ""
        parent = self.get_section_by_path(parent_path)
        
        if not parent:
            raise ValueError(f"Parent path '{parent_path}' not found")
            
        new_section = Section(title, content, parent)
        parent.subsections[title] = new_section
        return new_section

    def get_sections(self) -> Dict[str, Dict]:
        """Get a dictionary of all sections with their titles only"""
        def _build_section_dict(section: Section) -> Dict:
            return {
                "title": section.title,
                "subsections": {k: _build_section_dict(v) for k, v in section.subsections.items()}
            }
        
        return _build_section_dict(self.root)

    def save(self) -> None:
        """Save the biography to a JSON file using user_id."""
        os.makedirs(self.base_path, exist_ok=True)
            
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.root.to_dict(), f, indent=4, ensure_ascii=False)

    def update_section(self, path: str, content: str) -> Optional[Section]:
        """Update the content of a section at the specified path.
        Returns the updated section if found, None otherwise."""
        section = self.get_section_by_path(path)
        if section:
            section.content = content
            section.last_edit = datetime.now().isoformat()
            return section
        return None
