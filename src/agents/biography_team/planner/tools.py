from typing import Type, Optional, Callable, Dict


from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException
from pydantic import BaseModel, Field, SkipValidation


class AddPlanInput(BaseModel):
    action_type: str = Field(description="Type of action (create/update)")
    section_path: Optional[str] = Field(
        default=None,
        description="Optional: Full original path to the section"
    )
    section_title: Optional[str] = Field(
        default=None,
        description="Optional: Title of the section to update"
    )
    relevant_memories: Optional[str] = Field(
        default=None, 
        description="Optional: List of memories in bullet points format, e.g. '- Memory 1\n- Memory 2'"
    )
    update_plan: str = Field(description="Detailed plan for updating/creating the section")

class AddPlan(BaseTool):
    """Tool for adding a biography update plan."""
    name: str = "add_plan"
    description: str = "Add a plan for updating or creating a biography section"
    args_schema: Type[BaseModel] = AddPlanInput
    on_plan_added: SkipValidation[Callable[[Dict], None]] = Field(
        description="Callback function to be called when a plan is added"
    )

    def _run(
        self,
        action_type: str,
        update_plan: str,
        section_path: Optional[str] = None,
        section_title: Optional[str] = None,
        relevant_memories: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            plan = {
                "section_path": section_path,
                "section_title": section_title,
                "relevant_memories": relevant_memories.strip() if relevant_memories else 
None,
                "update_plan": update_plan
            }
            self.on_plan_added(plan)
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
    on_question_added: SkipValidation[Callable[[Dict], None]] = Field(
        description="Callback function to be called when a follow-up question is added"
    )

    def _run(
        self,
        content: str,
        context: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            question = {
                "content": content.strip(),
                "context": context.strip()
            }
            self.on_question_added(question)
            return f"Successfully added follow-up question: {content}"
        except Exception as e:
            raise ToolException(f"Error adding follow-up question: {str(e)}")