from typing import Type, Optional, Callable, Dict, List


from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException
from pydantic import BaseModel, Field, SkipValidation

from agents.biography_team.models import Plan, FollowUpQuestion


class AddPlanInput(BaseModel):
    action_type: str = Field(description="Type of action (create/update)")
    section_path: Optional[str] = Field(
        default=None,
        description=(
            "Full path to the section. "
            "Required when creating a new section."
            "But either section_path or section_title must be provided."
        )
    )
    section_title: Optional[str] = Field(
        default=None,
        description=(
            "Title of the section to update. "
            "Recommended when updating an existing section"
            "But either section_path or section_title must be provided."
        )
    )
    memory_ids: List[str] = Field(
        default=[], 
        description="Required: List of memory IDs that are relevant to this plan, e.g. ['MEM_03121423_X7K', 'MEM_03121423_X7K']"
    )
    update_plan: str = Field(description="Detailed plan for updating/creating the section")

class AddPlan(BaseTool):
    """Tool for adding a biography update plan."""
    name: str = "add_plan"
    description: str = "Add a plan for updating or creating a biography section"
    args_schema: Type[BaseModel] = AddPlanInput
    on_plan_added: SkipValidation[Callable[[Plan], None]] = Field(
        description="Callback function to be called when a plan is added"
    )

    def _run(
        self,
        action_type: str,
        update_plan: str,
        section_path: Optional[str] = None,
        section_title: Optional[str] = None,
        memory_ids: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            plan = {
                "section_path": section_path,
                "section_title": section_title,
                "memory_ids": memory_ids or [],  # Use empty list if None
                "update_plan": update_plan
            }
            self.on_plan_added(Plan(**plan))
            return f"Successfully added plan for {section_title}"
        except Exception as e:
            raise ToolException(f"Error adding plan: {str(e)}")

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
    on_question_added: SkipValidation[Callable[[FollowUpQuestion], None]] = Field(
        description="Callback function to be called when a follow-up question is added"
    )

    def _run(
        self,
        content: str,
        context: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            question = FollowUpQuestion(
                content=content.strip(),
                context=context.strip()
            )
            self.on_question_added(question)
            return f"Successfully added follow-up question: {content}"
        except Exception as e:
            raise ToolException(f"Error adding follow-up question: {str(e)}")