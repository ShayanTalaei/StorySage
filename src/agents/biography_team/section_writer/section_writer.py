from typing import Optional, TYPE_CHECKING, Type
from dataclasses import dataclass
from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException
from pydantic import BaseModel, Field


from agents.biography_team.base_biography_agent import BiographyConfig, BiographyTeamAgent
from agents.biography_team.models import TodoItem
from agents.biography_team.section_writer.prompts import SECTION_WRITER_PROMPT, USER_ADD_SECTION_PROMPT, USER_COMMENT_EDIT_PROMPT
from biography.biography_styles import BIOGRAPHY_STYLE_WRITER_INSTRUCTIONS
from agents.biography_team.section_writer.tools import GetSection, GetSectionByTitle, UpdateSection, UpdateSectionByTitle, AddSection, Recall

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession

@dataclass
class UpdateResult:
    success: bool
    message: str

class SectionWriter(BiographyTeamAgent):
    def __init__(self, config: BiographyConfig, interview_session: Optional['InterviewSession'] = None):
        super().__init__(
            name="SectionWriter",
            description="Updates individual biography sections based on plans",
            config=config,
            interview_session=interview_session
        )
        self.follow_up_questions = []
        
        self.tools = {
            "get_section": GetSection(biography=self.biography),
            "get_section_by_title": GetSectionByTitle(biography=self.biography),
            "update_section": UpdateSection(biography=self.biography),
            "update_section_by_title": UpdateSectionByTitle(biography=self.biography),
            "add_section": AddSection(biography=self.biography),
            "add_follow_up_question": AddFollowUpQuestion(section_writer=self),
            "recall": Recall(
                memory_bank=self.interview_session.memory_bank if interview_session else None,
                user_id=self.config.get("user_id") if not interview_session else None
            )
        }
    
    async def update_section(self, todo_item: TodoItem) -> UpdateResult:
        """Update a biography section based on a plan."""
        max_iterations = 3
        iterations = 0
        
        while iterations < max_iterations:
            prompt = self._create_section_write_prompt(todo_item)
            self.add_event(sender=self.name, tag="section_write_prompt", content=prompt)
            response = self.call_engine(prompt)
            self.add_event(sender=self.name, tag="section_write_response", content=response)
            
            try:
                if "<recall>" in response:
                    # Handle recall response
                    result = self.handle_tool_calls(response)
                    self.add_event(sender=self.name, tag="recall_response", content=result)
                    iterations += 1
                else:
                    # Handle section update
                    self.handle_tool_calls(response)
                    return UpdateResult(success=True, message="Section updated successfully")
                    
            except Exception as e:
                return UpdateResult(success=False, message=str(e))

    def _create_section_write_prompt(self, todo_item: TodoItem) -> str:
        """Create a prompt for the section writer to update a biography section."""
        # Add a new section based on user feedback
        if todo_item.action_type == "user_add":
            events_str = self.get_event_stream_str(
                filter=[{"sender": self.name, "tag": "recall_response"}]
            )
            return USER_ADD_SECTION_PROMPT.format(
                section_path=todo_item.section_path,
                update_plan=todo_item.update_plan,
                event_stream=events_str,
                style_instructions=BIOGRAPHY_STYLE_WRITER_INSTRUCTIONS.get(
                    self.config.get("biography_style", "chronological")
                ),
                tool_descriptions=self.get_tools_description(["recall", "add_section"])
            )
        # Update a section based on user feedback
        elif todo_item.action_type == "user_update":
            events_str = self.get_event_stream_str(
                filter=[{"sender": self.name, "tag": "recall_response"}]
            )
            current_content = self.tools["get_section_by_title"]._run(todo_item.section_title) or "Section does not exist yet."
            return USER_COMMENT_EDIT_PROMPT.format(
                section_title=todo_item.section_title,
                current_content=current_content,
                update_plan=todo_item.update_plan,
                event_stream=events_str,
                style_instructions=BIOGRAPHY_STYLE_WRITER_INSTRUCTIONS.get(
                    self.config.get("biography_style", "chronological")
                ),
                tool_descriptions=self.get_tools_description(["recall", "update_section_by_title"])
            )
        # Update a section based on newly collected memory
        else:
            section_identifier = todo_item.section_path or todo_item.section_title
            current_content = self.tools["get_section"]._run(section_identifier) or "Section does not exist yet."
            return SECTION_WRITER_PROMPT.format(
                section_path=section_identifier,
                update_plan=todo_item.update_plan,
                current_content=current_content,
                relevant_memories=todo_item.relevant_memories,
                style_instructions=BIOGRAPHY_STYLE_WRITER_INSTRUCTIONS.get(
                    self.config.get("biography_style", "chronological")
                ),
                tool_descriptions=self.get_tools_description()
            )

    def save_biography(self, save_markdown: bool = False) -> str:
        """Save the current state of the biography to file."""
        try:
            self.biography.save()
            if save_markdown:
                self.biography.export_to_markdown()
            return "Successfully saved biography to file"
        except Exception as e:
            error_msg = f"Error saving biography: {str(e)}"
            self.add_event(sender=self.name, tag="error", content=error_msg)
            return error_msg

class AddFollowUpQuestionInput(BaseModel):
    content: str = Field(description="The question to ask")
    context: str = Field(description="Context explaining why this question is important")

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