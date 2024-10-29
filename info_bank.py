import os
import json
from openai import OpenAI
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional

class Section:
    def __init__(self, name: str, content: Optional[str] = None):
        self.name = name
        self.content = content or ""
        self.subsections: List[Section] = []
        self.related_sections: List[Section] = []
        self.related_questions: List[str] = []

    def add_subsection(self, subsection: 'Section') -> None:
        self.subsections.append(subsection)

    def add_related_section(self, section: 'Section') -> None:
        self.related_sections.append(section)

    def add_related_question(self, question: str) -> None:
        self.related_questions.append(question)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "content": self.content,
            "subsections": [s.to_dict() for s in self.subsections],
            "related_sections": [s.name for s in self.related_sections],
            "related_questions": self.related_questions
        }

class InfoBank:
    def __init__(self):
        self.root = Section("Root")

    def add_section(self, path: str, content: str = "") -> None:
        keys = path.split('/')
        current = self.root
        for key in keys:
            existing = next((s for s in current.subsections if s.name == key), None)
            if existing:
                current = existing
            else:
                new_section = Section(key)
                current.add_subsection(new_section)
                current = new_section
        current.content = content

    def get_section(self, path: str) -> Optional[Section]:
        keys = path.split('/')
        current = self.root
        for key in keys:
            current = next((s for s in current.subsections if s.name == key), None)
            if current is None:
                return None
        return current

    def get_schema(self) -> dict:
        return self.root.to_dict()
    
    def get_formatted_state(self) -> str:
        """Returns a formatted XML representation of the current state"""
        def format_section(section, indent=0):
            indent_str = "  " * indent
            result = f"{indent_str}<section name='{section.name}'>\n"
            if section.content:
                result += f"{indent_str}  <content>{section.content}</content>\n"
            for subsection in section.subsections:
                result += format_section(subsection, indent + 2)
            result += f"{indent_str}</section>\n"
            return result

        return f"<info_bank>\n{format_section(self.root)}</info_bank>"
    
    