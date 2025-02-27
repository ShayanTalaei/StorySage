import os
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, ToolException
from typing import Type, Optional, Callable
from langchain_core.callbacks.manager import CallbackManagerForToolRun
from pydantic import BaseModel, Field, SkipValidation
from dotenv import load_dotenv

load_dotenv()

from content.question_bank.question_bank_base import QuestionBankBase
from content.session_note.session_note import SessionNote
from agents.biography_team.models import FollowUpQuestion

"""
Shared tools for updating the session notes:
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
    historical_question_bank: QuestionBankBase = Field(...)
    proposed_question_bank: Optional[QuestionBankBase] = Field(default=None)
    proposer: str = Field(...)

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
            # TODO: make it async and not blocking
            if os.getenv("EVAL_MODE", "FALSE").lower() == "true":
                self.historical_question_bank \
                    .evaluate_question_duplicate(question, self.proposer)
            
            if self.proposed_question_bank:
                self.proposed_question_bank.add_question(question)

            self.session_note.add_interview_question(
                topic=str(topic),
                question=str(question).strip(),
                question_id=str(question_id)
            )
            
            return f"Successfully added question {question_id} as follow-up to question"
        except Exception as e:
            raise ToolException(f"Error adding interview question: {str(e)}")
        

"""
Shared tools for proposing follow-up questions by:
- Planner
- Section writer

* Note: This tool only proposes follow-up questions, it does not really add them to the session notes, which is different from the add_interview_question tool.
"""

class ProposeFollowUpInput(BaseModel):
    content: str = Field(description="The question to ask")
    context: str = Field(description="Context explaining why this question is important")

class ProposeFollowUp(BaseTool):
    """Tool for adding follow-up questions."""
    name: str = "propose_follow_up"
    description: str = (
        "Add a follow-up question that needs to be asked to gather more information for the biography. "
        "Include both the question and context explaining why this information is needed."
    )
    args_schema: Type[BaseModel] = ProposeFollowUpInput
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