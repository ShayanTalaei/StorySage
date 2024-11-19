from typing import Dict, Type, Optional, Any
from pydantic import BaseModel, Field

import xml.etree.ElementTree as ET
from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException

from agents.base_agent import BaseAgent

from memory_bank.memory_bank_vector_db import MemoryBank
from biography.biography import Biography
from session_note.session_note import SessionNote
from interview_session.session_models import Participant
# Console colors
GREEN = '\033[92m'
ORANGE = '\033[93m'
RESET = '\033[0m'
RED = '\033[91m'

class Biographer(BaseAgent, Participant):
    def __init__(self, config: Dict):
        super().__init__(
            name="Biographer",
            description="Agent responsible for writing and maintaining the user's biography",
            config=config
        )
        
        user_id = config.get("user_id")
        self.memory_bank = MemoryBank.load_from_file(user_id)
        self.session_notes = SessionNote.get_last_session_note(user_id)
        self.biography = Biography.load_from_file(user_id)
        
        self.tools = {
            "recall": Recall(memory_bank=self.memory_bank),
            "get_section": GetSection(biography=self.biography),
            "add_section": AddSection(biography=self.biography),
            "update_section": UpdateSection(biography=self.biography)
        }
        
        # Initialize with system message
        intro_system_message = BIOGRAPHER_SYSTEM_MESSAGE.format(
            biography_structure=self.biography.get_sections(),
            session_notes=config.get("session_notes", "No previous session notes available."),
            tool_descriptions=self.get_tools_description()
        )
        self.event_stream.append(("system", intro_system_message))
        

    def workout(self, session_summary: str):
        
        
        while True:
            messages = self.get_event_stream_str()
            response = self.call_engine(messages) ## TODO: Create the prompt, add session summary
            
            self.handle_tool_calls(response)
            if "<session_notes>" in response:
                notes_start = response.find("<session_notes>") + len("<session_notes>")
                notes_end = response.find("</session_notes>")
                session_notes = response[notes_start:notes_end].strip()
                
                # Save biography and return session notes
                self.biography.save()
                return session_notes
            
    def format_session_notes(self):
        return self.session_notes.to_str()

class RecallInput(BaseModel):
    query: str = Field(description="Query to search for relevant memories")

class GetSectionInput(BaseModel):
    title: str = Field(description="Title of the section to retrieve")

class AddSectionInput(BaseModel):
    path: str = Field(description="Path where to add the section (e.g., 'Chapter 1/Early Life')")
    title: str = Field(description="Title of the new section")
    content: str = Field(description="Content of the new section")

class UpdateSectionInput(BaseModel):
    path: str = Field(description="Path to the section to update")
    content: str = Field(description="New content for the section")

class Recall(BaseTool):
    name: str = "recall"
    description: str = "Search for relevant memories in the memory bank"
    args_schema: Type[BaseModel] = RecallInput
    memory_bank: MemoryBank

    def _run(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        try:
            memories = self.memory_bank.search_memories(query)
            return "\n".join([f"Memory {i+1}:\n{memory['text']}" for i, memory in enumerate(memories)])
        except Exception as e:
            raise ToolException(f"Error recalling memories: {e}")

class GetSection(BaseTool):
    name: str = "get_section"
    description: str = "Retrieve content of a biography section by its title"
    args_schema: Type[BaseModel] = GetSectionInput
    biography: Biography

    def _run(self, title: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        section = self.biography.get_section_by_title(title)
        if not section:
            return f"Section '{title}' not found"
        return section.content

class AddSection(BaseTool):
    name: str = "add_section"
    description: str = "Add a new section to the biography"
    args_schema: Type[BaseModel] = AddSectionInput
    biography: Biography

    def _run(self, path: str, title: str, content: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        try:
            self.biography.add_section(path, title, content)
            return f"Successfully added section '{title}' at path '{path}'"
        except Exception as e:
            raise ToolException(f"Error adding section: {e}")

class UpdateSection(BaseTool):
    name: str = "update_section"
    description: str = "Update content of an existing section"
    args_schema: Type[BaseModel] = UpdateSectionInput
    biography: Biography

    def _run(self, path: str, content: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        section = self.biography.update_section(path, content)
        if not section:
            raise ToolException(f"Section at path '{path}' not found")
        return f"Successfully updated section at path '{path}'"

BIOGRAPHER_SYSTEM_MESSAGE = """You are a professional biographer. Your task is to write and maintain a biography based on interviews with the subject.

Current biography structure:
{biography_structure}

Previous session notes:
{session_notes}

Available tools:
{tool_descriptions}

Your task is to:
1. Review the latest interview
2. Update or add biography sections as needed
3. Create session notes for the next interview, including:
   - General information about the user
   - Summary of the last meeting
   - Specific questions to ask in the next session

Use the tools to:
- Recall memories using the recall tool
- Read existing biography sections using get_section
- Add new sections using add_section
- Update existing sections using update_section

When you're done, provide the new session notes within <session_notes> tags.
""" 