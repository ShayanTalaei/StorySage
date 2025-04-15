from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, ToolException
from typing import Type, Optional
from langchain_core.callbacks.manager import CallbackManagerForToolRun


from content.session_agenda.session_agenda import SessionAgenda

class UpdateLastMeetingSummaryInput(BaseModel):
    summary: str = Field(description="The new summary text for the last meeting")

class UpdateLastMeetingSummary(BaseTool):
    """Tool for updating the last meeting summary."""
    name: str = "update_last_meeting_summary"
    description: str = "Updates the last meeting summary in the session agenda"
    args_schema: Type[BaseModel] = UpdateLastMeetingSummaryInput
    session_agenda: SessionAgenda = Field(...)

    def _run(
        self,
        summary: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            self.session_agenda.last_meeting_summary = summary.strip()
            return "Successfully updated last meeting summary"
        except Exception as e:
            raise ToolException(f"Error updating last meeting summary: {e}")

class UpdateUserPortraitInput(BaseModel):
    field_name: str = Field(description="The name of the field to update or create")
    value: str = Field(description="The new value for the field")
    is_new_field: bool = Field(description="Whether this is a new field (True) or updating existing field (False)")
    reasoning: str = Field(description="Explanation for why this update/creation is important")

class UpdateUserPortrait(BaseTool):
    """Tool for updating the user portrait."""
    name: str = "update_user_portrait"
    description: str = (
        "Updates or creates a field in the user portrait. "
        "Use is_new_field=True for creating new fields, False for updating existing ones. "
        "Provide clear reasoning for why the update/creation is important."
    )
    args_schema: Type[BaseModel] = UpdateUserPortraitInput
    session_agenda: SessionAgenda = Field(...)

    def _run(
        self,
        field_name: str,
        value: str,
        is_new_field: bool,
        reasoning: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            formatted_field_name = " ".join(word.capitalize() for word in field_name.replace("_", " ").split())
            value_str = str(value)
            cleaned_value = value_str.strip('[]').strip()
            self.session_agenda.user_portrait[formatted_field_name] = cleaned_value
            action = "Created new field" if is_new_field else "Updated field"
            return f"{action}: {formatted_field_name}\nReasoning: {reasoning}"
        except Exception as e:
            raise ToolException(f"Error updating user portrait: {e}")


class DeleteInterviewQuestionInput(BaseModel):
    question_id: str = Field(description="The ID of the question to delete")
    reasoning: str = Field(
        description="Explain why this question should be deleted. For example:\n"
        "- Question has comprehensive answers/notes\n"
        "- All important aspects are covered\n"
    )

class DeleteInterviewQuestion(BaseTool):
    """Tool for deleting interview questions."""
    name: str = "delete_interview_question"
    description: str = (
        "Deletes an interview question from the session agenda. "
        "If the question has sub-questions, it will clear the question text and notes "
        "but keep the sub-questions. If it has no sub-questions, it will be completely removed. "
        "Provide clear reasoning for why the question should be deleted."
    )
    args_schema: Type[BaseModel] = DeleteInterviewQuestionInput
    session_agenda: SessionAgenda = Field(...)

    def _run(
        self,
        question_id: str,
        reasoning: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            self.session_agenda.delete_interview_question(str(question_id))
            return f"Successfully deleted question {question_id}. Reason: {reasoning}"
        except Exception as e:
            raise ToolException(f"Error deleting interview question: {str(e)}")
