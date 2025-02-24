from typing import Optional, Type
from pydantic import BaseModel, Field
from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException


from content.biography.biography import Biography


class UpdateSectionInput(BaseModel):
    path: Optional[str] = Field(description="Original full path to the section to update. Optional if you want to update the title instead.", default=None)
    title: Optional[str] = Field(description="Title of the section to update. Optional if you want to update the content instead.", default=None)
    content: str = Field(description="Updated content for the section")
    new_title: Optional[str] = Field(description="Updated title for the section. Only provide if you want to change the title.", default=None)

class UpdateSection(BaseTool):
    """Tool for updating existing sections."""
    name: str = "update_section"
    description: str = "Update content of an existing section"
    args_schema: Type[BaseModel] = UpdateSectionInput
    biography: Biography

    async def _run(
        self,
        content: str,
        path: Optional[str] = None,
        title: Optional[str] = None,
        new_title: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        section = await self.biography.update_section(
            path=path,
            title=title,
            content=content,
            new_title=new_title
        )
        if not section:
            identifier = path if path else title
            raise ToolException(f"Section '{identifier}' not found")
        return f"Successfully updated section '{path if path else title}'"


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

    async def _run(self, path: str, content: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        try:
            await self.biography.add_section(path, content)
            return f"Successfully added section at path '{path}'"
        except Exception as e:
            raise ToolException(f"Error adding section: {e}")
