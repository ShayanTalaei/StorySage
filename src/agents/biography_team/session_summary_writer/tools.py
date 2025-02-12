from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, ToolException
from typing import Type, Optional
from langchain_core.callbacks.manager import CallbackManagerForToolRun


from memory_bank.memory_bank_base import MemoryBankBase
from session_note.session_note import SessionNote

class UpdateLastMeetingSummaryInput(BaseModel):
    summary: str = Field(description="The new summary text for the last meeting")

class UpdateLastMeetingSummary(BaseTool):
    """Tool for updating the last meeting summary."""
    name: str = "update_last_meeting_summary"
    description: str = "Updates the last meeting summary in the session note"
    args_schema: Type[BaseModel] = UpdateLastMeetingSummaryInput
    session_note: SessionNote = Field(...)

    def _run(
        self,
        summary: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            self.session_note.last_meeting_summary = summary.strip()
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
    session_note: SessionNote = Field(...)

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
            self.session_note.user_portrait[formatted_field_name] = cleaned_value
            action = "Created new field" if is_new_field else "Updated field"
            return f"{action}: {formatted_field_name}\nReasoning: {reasoning}"
        except Exception as e:
            raise ToolException(f"Error updating user portrait: {e}")

class AddInterviewQuestionInput(BaseModel):
    topic: str = Field(description="The topic category for the question (e.g., 'Career', 'Education')")
    question: str = Field(description="The actual question text")
    question_id: str = Field(description="The ID for the question (e.g., '1', '1.1', '2.3')")
    # parent_id: str = Field(description="The ID of the parent question (e.g., '1', '2', etc.). Still include it but leave it empty if it is a top-level question.")
    # parent_text: str = Field(description="The text of the parent question. Still include it but leave it empty if it is a top-level question.")

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
        # parent_id: str,
        # parent_text: str,
        question_id: str,
        question: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:

            self.session_note.add_interview_question(
                topic=str(topic),
                question=str(question).strip(),
                question_id=str(question_id)
            )
            
            return f"Added parent question {question_id} as follow-up."
        except Exception as e:
            raise ToolException(f"Error adding interview question: {str(e)}")

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
        "Deletes an interview question from the session notes. "
        "If the question has sub-questions, it will clear the question text and notes "
        "but keep the sub-questions. If it has no sub-questions, it will be completely removed. "
        "Provide clear reasoning for why the question should be deleted."
    )
    args_schema: Type[BaseModel] = DeleteInterviewQuestionInput
    session_note: SessionNote = Field(...)

    def _run(
        self,
        question_id: str,
        reasoning: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            self.session_note.delete_interview_question(str(question_id))
            return f"Successfully deleted question {question_id}. Reason: {reasoning}"
        except Exception as e:
            raise ToolException(f"Error deleting interview question: {str(e)}")

class RecallInput(BaseModel):
    reasoning: str = Field(
        description="Explain:\n"
        "1. What information you're looking for\n"
        "2. How this search will help evaluate multiple related questions\n"
        "3. What decisions this search will inform"
    )
    query: str = Field(
        description="The search query to find relevant information. Make it broad enough to cover related topics."
    )

class Recall(BaseTool):
    """Tool for recalling memories."""
    name: str = "recall"
    description: str = (
        "A tool for recalling memories. "
        "Use this tool to check if we already have relevant information about a topic "
        "before deciding to propose or delete questions in the session notes. "
        "Explain your search intent and how the results will guide your decision."
    )
    args_schema: Type[BaseModel] = RecallInput
    memory_bank: MemoryBankBase = Field(...)

    def _run(
        self,
        query: str,
        reasoning: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            memories = self.memory_bank.search_memories(query)
            memories_str = "\n".join([f"<memory>{memory['text']}</memory>" for memory in memories])
            return f"""\
<memory_search>
<query>{query}</query>
<reasoning>
{reasoning}
</reasoning>
<results>
{memories_str}
</results>
</memory_search>
""" if memories_str else f"""\
<memory_search>
<query>{query}</query>
<reasoning>
{reasoning}
</reasoning>
<results>No relevant memories found.</results>
</memory_search>"""
        except Exception as e:
            raise ToolException(f"Error recalling memories: {e}")