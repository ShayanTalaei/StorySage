from typing import Type, Optional, TYPE_CHECKING
from dataclasses import dataclass
from pydantic import BaseModel, Field
from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException

from agents.biography_team.base_biography_agent import BiographyConfig, BiographyTeamAgent
from agents.biography_team.models import TodoItem
from agents.biography_team.section_writer.prompts import SECTION_WRITER_PROMPT
from biography.biography import Biography
from biography.biography_styles import BIOGRAPHY_STYLE_WRITER_INSTRUCTIONS

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession

@dataclass
class UpdateResult:
    success: bool
    message: str

class SectionWriter(BiographyTeamAgent):
    def __init__(self, config: BiographyConfig, interview_session: 'InterviewSession'):
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
            "add_follow_up_question": AddFollowUpQuestion(section_writer=self)
        }
        
    async def update_section(self, todo_item: TodoItem) -> UpdateResult:
        """Update a biography section based on a plan."""
        prompt = self._create_section_write_prompt(todo_item)
        self.add_event(sender=self.name, tag="prompt", content=prompt)
        response = self.call_engine(prompt)
        self.add_event(sender=self.name, tag="llm_response", content=response)
        
        try:
            # Handle tool calls
            self.handle_tool_calls(response)
            
            result_message = "Section updated successfully"
            self.add_event(sender=self.name, tag="event_result", content=result_message)
            
            return UpdateResult(success=True, message=result_message)
            
        except Exception as e:
            error_msg = f"Error updating section: {str(e)}"
            self.add_event(sender=self.name, tag="error", content=error_msg)
            return UpdateResult(success=False, message=error_msg)

    def _create_section_write_prompt(self, todo_item: TodoItem) -> str:
        """Create a prompt for the section writer to update a biography section."""
        current_content = self.tools["get_section"]._run(todo_item.section_path) or "Section does not exist yet."
                
        return SECTION_WRITER_PROMPT.format(
            section_path=todo_item.section_path,
            update_plan=todo_item.update_plan,
            current_content=current_content,
            relevant_memories='\n'.join([
                f"- {memory_text}"
                for memory_text in todo_item.relevant_memories
            ]),
            style_instructions=BIOGRAPHY_STYLE_WRITER_INSTRUCTIONS.get(
                self.config.get("biography_style", "chronological")
            ),
            tool_descriptions=self.get_tools_description()
        )

    def save_biography(self) -> str:
        """Save the current state of the biography to file."""
        try:
            self.biography.save()
            self.biography.export_to_markdown()
            return "Successfully saved biography to file"
        except Exception as e:
            error_msg = f"Error saving biography: {str(e)}"
            self.add_event(sender=self.name, tag="error", content=error_msg)
            return error_msg

class UpdateSectionInput(BaseModel):
    path: str = Field(description="Path to the section to update")
    content: str = Field(description="New content for the section")

class AddSectionInput(BaseModel):
    path: str = Field(description="Full path to the new section (e.g., '1 Early Life/1.1 Childhood')")
    content: str = Field(description="Content of the new section")

class AddFollowUpQuestionInput(BaseModel):
    content: str = Field(description="The question to ask")
    context: str = Field(description="Context explaining why this question is important")

class GetSection(BaseTool):
    """Tool for retrieving section content."""
    name: str = "get_section"
    description: str = "Retrieve content of a biography section by its path"
    # args_schema: Type[BaseModel] = GetSectionInput # TODO: Allow agent to use this tool
    biography: Biography

    def _run(self, path: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        section = self.biography.get_section_by_path(path)
        if not section:
            return ""
        return section.content

class UpdateSection(BaseTool):
    """Tool for updating existing sections."""
    name: str = "update_section"
    description: str = "Update content of an existing section"
    args_schema: Type[BaseModel] = UpdateSectionInput
    biography: Biography

    def _run(self, path: str, content: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        section = self.biography.update_section(path=path, content=content)
        if not section:
            raise ToolException(f"Section at path '{path}' not found")
        return f"Successfully updated section at path '{path}'"

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

class AddFollowUpQuestion(BaseTool):
    """Tool for adding follow-up questions."""
    name: str = "add_follow_up_question"
    description: str = (
        "Add a follow-up question that needs to be asked to gather more information for the biography. "
        "Include both the question and context explaining why this information is needed."
    )
    args_schema: Type[BaseModel] = AddFollowUpQuestionInput
    section_writer: SectionWriter = Field(...)

    def _run(
        self,
        content: str,
        context: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            self.section_writer.follow_up_questions.append({
                "content": content.strip(),
                "context": context.strip()
            })
            return f"Successfully added follow-up question: {content}"
        except Exception as e:
            raise ToolException(f"Error adding follow-up question: {str(e)}")