from typing import Dict, List, Type, Optional, TYPE_CHECKING
from dataclasses import dataclass
from pydantic import BaseModel, Field
from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException

from agents.biography_team.base_biography_agent import BiographyTeamAgent
from agents.biography_team.models import TodoItem
import xml.etree.ElementTree as ET

from biography.biography import Biography

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession

@dataclass
class UpdateResult:
    success: bool
    message: str

class SectionWriter(BiographyTeamAgent):
    def __init__(self, config: Dict, interview_session: 'InterviewSession'):
        super().__init__(
            name="SectionWriter",
            description="Updates individual biography sections based on plans",
            config=config,
            interview_session=interview_session
        )
        self.follow_up_questions = []
        
        self.tools = {
            "get_section": GetSection(biography=self.biography),
            "update_section": UpdateSection(biography=self.biography),
            "add_section": AddSection(biography=self.biography),
            "save_biography": SaveBiography(biography=self.biography)
        }
        
    async def update_section(self, todo_item: TodoItem) -> UpdateResult:
        prompt = self._create_section_write_prompt(todo_item)
        response = self.call_engine(prompt)
        
        # Parse response and update section
        success = self._handle_section_update(response, todo_item)
        self.follow_up_questions.extend(self._parse_questions(response))
        
        return UpdateResult(
            success=success,
            message="Section updated successfully" if success else "Failed to update section"
        )

    def save_biography(self) -> str:
        """Save the current state of the biography to file."""
        return self.tools["save_biography"]._run()

    def _create_section_write_prompt(self, todo_item: TodoItem) -> str:
        return SECTION_WRITER_PROMPT.format(
            section_path=todo_item.section_path,
            update_plan=todo_item.update_plan,
            current_content=self.tools["get_section"]._run(todo_item.section_path) or "Section does not exist yet."
        )

    def _handle_section_update(self, response: str, todo_item: TodoItem) -> bool:
        try:
            if todo_item.action_type == "update" and "<section_update>" in response:
                start_tag = "<section_update>"
                end_tag = "</section_update>"
                start_pos = response.find(start_tag)
                end_pos = response.find(end_tag) + len(end_tag)
                update_text = response[start_pos:end_pos]
                root = ET.fromstring(update_text)
                content = root.find("content").text.strip()
                
                # Use the update_section tool to apply changes
                result = self.tools["update_section"]._run(
                    path=todo_item.section_path,
                    content=content
                )
                return "Successfully" in result

            elif todo_item.action_type == "create" and "<section_update>" in response:
                start_tag = "<section_update>"
                end_tag = "</section_update>"
                start_pos = response.find(start_tag)
                end_pos = response.find(end_tag) + len(end_tag)
                update_text = response[start_pos:end_pos]
                root = ET.fromstring(update_text)
                content = root.find("content").text.strip()
                
                # Use the add_section tool to create a new section
                result = self.tools["add_section"]._run(
                    path=todo_item.section_path,
                    title=todo_item.section_title,
                    content=content
                )
                return "Successfully" in result

        except Exception as e:
            print(f"Error updating section: {e}")
            return False
        return False

    def _parse_questions(self, response: str) -> List[Dict]:
        questions = []
        if "<follow_up_questions>" in response:
            start_tag = "<follow_up_questions>"
            end_tag = "</follow_up_questions>"
            start_pos = response.find(start_tag)
            end_pos = response.find(end_tag) + len(end_tag)
            questions_text = response[start_pos:end_pos]
            root = ET.fromstring(questions_text)
            for question in root.findall("question"):
                questions.append({
                    "question": question.text.strip(),
                    "type": "depth"
                })
        return questions

SECTION_WRITER_PROMPT = """
You are a biography writer. Your task is to update or create a section of the biography and suggest follow-up questions to deepen the section.

Section Path: 
<section_path>
{section_path}
</section_path>

Update Plan: 
<update_plan>
{update_plan}
</update_plan>

Current Content of the Section:
<current_content>
{current_content}
</current_content>

Please write the updated section content and suggest follow-up questions to deepen this section.

Provide your response in the following XML format:
<section_update>
    <content>Updated section content</content>
</section_update>
<follow_up_questions>
    <question>Question text</question>
    ...
</follow_up_questions>
"""

class GetSectionInput(BaseModel):
    path: str = Field(description="Path to the section to retrieve")

class UpdateSectionInput(BaseModel):
    path: str = Field(description="Path to the section to update")
    content: str = Field(description="New content for the section")

class AddSectionInput(BaseModel):
    path: str = Field(description="Path where to add the section (e.g., 'Chapter 1/Early Life')")
    title: str = Field(description="Title of the new section")
    content: str = Field(description="Content of the new section")

class SaveBiographyInput(BaseModel):
    pass  # No input needed for saving

class SaveBiography(BaseTool):
    name: str = "save_biography"
    description: str = "Save the current state of the biography to file"
    args_schema: Type[BaseModel] = SaveBiographyInput
    biography: Biography

    def _run(self, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        try:
            self.biography.save()
            return "Successfully saved biography to file"
        except Exception as e:
            raise ToolException(f"Error saving biography: {e}")

class GetSection(BaseTool):
    name: str = "get_section"
    description: str = "Retrieve content of a biography section by its path"
    args_schema: Type[BaseModel] = GetSectionInput
    biography: Biography

    def _run(self, path: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        section = self.biography.get_section_by_path(path)
        if not section:
            return f"Section at path '{path}' not found"
        return section.content

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