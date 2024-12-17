from datetime import datetime
import json
from typing import Dict, Optional
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
        self.version = self._get_next_version()
        self.file_name = f"{self.base_path}/biography_{self.version}"
        self.root = Section(f"Biography of {self.user_id}")

    def _get_next_version(self) -> int:
        """Get the next available version number for the biography file.
        
        Scans the directory for existing biography files and returns
        the next available version number.
        
        Example:
            If directory contains: biography_1.json, biography_2.json
            Returns: 3
        """
        # List all biography JSON files
        files = [f for f in os.listdir(self.base_path) 
                if f.startswith('biography_') and f.endswith('.json')]
        
        if not files:
            return 1
            
        # Extract version numbers from filenames
        versions = []
        for file in files:
            try:
                version = int(file.replace('biography_', '').replace('.json', ''))
                versions.append(version)
            except ValueError:
                continue
                
        next_version = max(versions) + 1 if versions else 1
        print(f"Next version: {next_version}")
        return next_version

    @classmethod
    def load_from_file(cls, user_id: str, version: int = -1) -> 'Biography':
        """Load a biography from file or create new one if it doesn't exist.
        
        Args:
            user_id: The ID of the user
            version: Optional specific version to load. If None, loads latest version.
        """
        biography = cls(user_id)
        
        if version > 0:
            # Load specific version
            file_path = f"{biography.base_path}/biography_{version}.json"
        else:
            # Use latest version (next version - 1)
            latest_version = biography._get_next_version() - 1
            if latest_version < 1:
                return biography
            file_path = f"{biography.base_path}/biography_{latest_version}.json"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                biography.root = Section.from_dict(data)
                biography.version = version if version > 0 else latest_version
        except FileNotFoundError:
            pass
        
        return biography

    def get_section_by_path(self, path: str) -> Optional[Section]:
        """Get a section using its path (e.g., 'Chapter 1/Section 1.1')"""
        if not path:
            return self.root

        if path and not self.is_valid_path_format(path):
            raise ValueError(f"Invalid path format: {path}. Path must follow the required format rules.")

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

    def add_section(self, path: str, content: str = "") -> Section:
        """Add a new section at the specified path, creating parent sections if they don't exist."""
        if not path:
            raise ValueError("Path cannot be empty - must provide a section path")
        
        if not self.is_valid_path_format(path):
            raise ValueError(f"Invalid path format: {path}. Path must follow the required format rules.")

        # Split the path into parts
        path_parts = path.split('/')
        title = path_parts[-1]
        
        # Get or create the parent section
        current = self.root
        for part in path_parts[:-1]:  # Exclude the last part (which is the new section's title)
            if part not in current.subsections:
                # Create missing parent section
                new_parent = Section(part, "", current)
                current.subsections[part] = new_parent
            current = current.subsections[part]
        
        # Create and add the new section
        new_section = Section(title, content, current)
        current.subsections[path_parts[-1]] = new_section
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
            
        with open(f'{self.file_name}.json', 'w', encoding='utf-8') as f:
            json.dump(self.root.to_dict(), f, indent=4, ensure_ascii=False)

    def update_section(self, path: str, content: str) -> Optional[Section]:
        """Update the content of a section at the specified path.
        Returns the updated section if found, None otherwise."""
        if not path:
            raise ValueError("Path cannot be empty - must provide a section path")
        
        if not self.is_valid_path_format(path):
            raise ValueError(f"Invalid path format: {path}. Path must follow the required format rules.")
        
        section = self.get_section_by_path(path)
        if section:
            section.content = content
            section.last_edit = datetime.now().isoformat()
            return section
        return None

    def export_to_markdown(self) -> str:
        """Convert the biography to markdown format and save to file.
        Returns the markdown string."""
        def _section_to_markdown(section: Section, level: int = 1) -> str:
            # Convert section to markdown with appropriate heading level
            md = f"{'#' * level} {section.title}\n\n"
            if section.content:
                md += f"{section.content}\n\n"
            
            # Process subsections recursively
            for subsection in section.subsections.values():
                md += _section_to_markdown(subsection, level + 1)
            
            return md

        # Generate markdown content
        markdown_content = _section_to_markdown(self.root)

        # Save to markdown file
        output_path = f"{self.file_name}.md"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        return markdown_content
    
    @classmethod
    def export_to_markdown_from_file(cls, json_path: str) -> str:
        """Convert a biography JSON file to markdown format and save it.
        
        Args:
            json_path: Path to the biography JSON file
            
        Returns:
            str: The generated markdown content
            
        Example:
            Biography.export_to_markdown_from_file("data/user123/biography_1.json")
            # Creates: data/user123/biography_1.md
        """
        # Load and validate JSON file
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            root = Section.from_dict(data)
        except FileNotFoundError:
            raise FileNotFoundError(f"Biography file not found: {json_path}")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON file: {json_path}")
        
        def _section_to_markdown(section: Section, level: int = 1) -> str:
            # Convert section to markdown with appropriate heading level
            md = f"{'#' * level} {section.title}\n\n"
            if section.content:
                md += f"{section.content}\n\n"
            
            # Process subsections recursively
            for subsection in section.subsections.values():
                md += _section_to_markdown(subsection, level + 1)
            
            return md

        # Generate markdown content
        markdown_content = _section_to_markdown(root)

        # Save to markdown file
        output_path = json_path.replace('.json', '.md')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        return markdown_content

    def is_valid_path_format(self, path: str) -> bool:
        """
        Validate if the path follows the required format rules.
        Returns True if valid, False otherwise.
        """
        if not path:
            return True  # Empty path is valid (root)

        parts = path.split('/')
        
        # Check maximum depth
        if len(parts) > 4:
            return False
            
        # Validate first level requires number prefix
        if not parts[0].split()[0].isdigit():
            return False
            
        # Validate second level requires decimal notation
        if len(parts) > 1:
            if not self._is_valid_subsection_number(parts[0], parts[1]):
                return False
                
        # Third and fourth levels should not have numbers
        if len(parts) > 2:
            for part in parts[2:]:
                if part.split()[0].replace('.', '').isdigit():
                    return False
                    
        return True

    def _is_valid_subsection_number(self, parent: str, child: str) -> bool:
        """
        Validate if subsection number matches parent section number.
        Example: "1 Early Life" -> oytho is valid
        """
        try:
            parent_num = parent.split()[0]
            child_num = child.split()[0]
            if not child_num.count('.') == 1:
                return False
            return child_num.startswith(f"{parent_num}.")
        except (IndexError, ValueError):
            return False

    def path_exists(self, path: str) -> bool:
        """
        Check if a given path exists in the biography.
        Returns True if the path exists, False otherwise.
        """
        if not self.is_valid_path_format(path):
            return False
        return self.get_section_by_path(path) is not None