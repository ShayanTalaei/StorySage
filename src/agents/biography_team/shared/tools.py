from typing import Type, Optional, Callable


from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException
from pydantic import BaseModel, Field, SkipValidation

from agents.biography_team.shared.models import FollowUpQuestion

"""
Tools shared by:
- Planner
- Section writer
"""

class AddFollowUpQuestionInput(BaseModel):
    content: str = Field(description="The question to ask")
    context: str = Field(description="Context explaining why this question is important")

# Shared by both planner and section_writer
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