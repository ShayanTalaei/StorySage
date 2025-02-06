from typing import Optional, Type
from pydantic import BaseModel, Field
from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException


from biography.biography import Biography
from memory_bank.memory_bank_vector_db import MemoryBank


class GetSectionInput(BaseModel):
    path: str = Field(description="Path to the section to retrieve")


class GetSection(BaseTool):
    """Tool for retrieving section content."""
    name: str = "get_section"
    description: str = "Retrieve content of a biography section by its path"
    args_schema: Type[BaseModel] = GetSectionInput
    biography: Biography

    def _run(self, path: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        section = self.biography.get_section_by_path(path)
        if not section:
            return ""
        return section.content


class GetSectionByTitleInput(BaseModel):
    title: str = Field(description="Title of the section to retrieve")


class GetSectionByTitle(BaseTool):
    """Tool for retrieving section content by title."""
    name: str = "get_section_by_title"
    description: str = "Retrieve content of a biography section by its title"
    args_schema: Type[BaseModel] = GetSectionByTitleInput
    biography: Biography

    def _run(self, title: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        section = self.biography.get_section_by_title(title)
        if not section:
            return ""
        return section.content


class UpdateSectionInput(BaseModel):
    path: str = Field(description="Original Path to the section to update")
    content: str = Field(description="Updated content for the section")
    new_title: Optional[str] = Field(description="Updated title for the section", default=None)

class UpdateSection(BaseTool):
    """Tool for updating existing sections."""
    name: str = "update_section"
    description: str = "Update content of an existing section"
    args_schema: Type[BaseModel] = UpdateSectionInput
    biography: Biography

    def _run(self, path: str, content: str, new_title: Optional[str] = None, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        section = self.biography.update_section(path=path, content=content, new_title=new_title)
        if not section:
            raise ToolException(f"Section at path '{path}' not found")
        return f"Successfully updated section at path '{path}'"


class UpdateSectionByTitleInput(BaseModel):
    title: str = Field(description="Title of the section to update")
    content: str = Field(description="New content for the section")


class UpdateSectionByTitle(BaseTool):
    """Tool for updating existing sections by title."""
    name: str = "update_section_by_title"
    description: str = "Update content of an existing section using its title"
    args_schema: Type[BaseModel] = UpdateSectionByTitleInput
    biography: Biography

    def _run(self, title: str, content: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        section = self.biography.update_section(title=title, content=content)
        if not section:
            raise ToolException(f"Section with title '{title}' not found")
        return f"Successfully updated section with title '{title}'"


class AddSectionInput(BaseModel):
    path: str = Field(
        description="Full path to the new section (e.g., '1 Early Life/1.1 Childhood')")
    content: str = Field(description="Content of the new section")


class AddSection(BaseTool):
    """Tool for adding new sections."""
    name: str = "add_section"
    description: str = "Add a new section to the biography"
    args_schema: Type[BaseModel] = AddSectionInput
    biography: Biography

    def _run(self, path: str, content: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        try:
            self.biography.add_section(path, content)
            return f"Successfully added section at path '{path}'"
        except Exception as e:
            raise ToolException(f"Error adding section: {e}")


class RecallInput(BaseModel):
    reasoning: str = Field(description="Explain how this information helps the section")
    query: str = Field(description="Search query to find relevant memories")

class Recall(BaseTool):
    """Tool for searching relevant memories."""
    name: str = "recall"
    description: str = "Search for relevant memories before writing/updating sections"
    args_schema: Type[BaseModel] = RecallInput
    memory_bank: Optional[MemoryBank] = Field(default=None)
    user_id: Optional[str] = Field(default=None)

    def _run(self, query: str, reasoning: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        try:
            # Load memory bank from file if not provided
            if self.memory_bank is None and self.user_id:
                self.memory_bank = MemoryBank.load_from_file(self.user_id)
            
            if self.memory_bank is None:
                raise ToolException("No memory bank available")

            memories = self.memory_bank.search_memories(query)
            memories_str = "\n".join([f"<memory>{memory['text']}</memory>" for memory in memories])
            return f"""\
<memory_search>
<query>{query}</query>
<reasoning>{reasoning}</reasoning>
<results>
{memories_str if memories_str else "No relevant memories found."}
</results>
</memory_search>"""
        except Exception as e:
            raise ToolException(f"Error searching memories: {e}")

