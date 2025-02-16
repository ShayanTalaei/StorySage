from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, ToolException
from typing import Type, Optional
from langchain_core.callbacks.manager import CallbackManagerForToolRun


from content.session_note.session_note import SessionNote

"""
Shared tools for note taking by:
- Note taker
- Session summary writer
"""

class AddInterviewQuestionInput(BaseModel):
    topic: str = Field(description="The topic category for the question (e.g., 'Career', 'Education')")
    question: str = Field(description="The actual question text")
    question_id: str = Field(description="The ID for the question (e.g., '1', '1.1', '2.3')")
    parent_id: Optional[str] = Field(default=None, description="The ID of the parent question (e.g., '1', '2', etc.). No need to include if it is a top-level question.")
    parent_text: Optional[str] = Field(default=None, description="The text of the parent question. No need to include if it is a top-level question.")

class AddInterviewQuestion(BaseTool):
    """Tool for adding new interview questions."""
    name: str = "add_interview_question"
    description: str = (
        "Adds a new interview question to the session notes. "
    )
    args_schema: Type[BaseModel] = AddInterviewQuestionInput
    session_note: SessionNote = Field(...)

    def _run(
        self,
        topic: str,
        question_id: str,
        question: str,
        parent_id: Optional[str] = None,
        parent_text: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:

            self.session_note.add_interview_question(
                topic=str(topic),
                question=str(question).strip(),
                question_id=str(question_id)
            )
            
            return f"Successfully added question {question_id} as follow-up to question"
        except Exception as e:
            raise ToolException(f"Error adding interview question: {str(e)}")