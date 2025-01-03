from typing import Dict, List, TYPE_CHECKING
from agents.biography_team.base_biography_agent import BiographyConfig, BiographyTeamAgent
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, ToolException
from typing import Type, Optional
from langchain_core.callbacks.manager import CallbackManagerForToolRun

from agents.biography_team.prompts import SESSION_NOTE_AGENT_PROMPT
from session_note.session_note import SessionNote

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession

class SessionSummaryWriter(BiographyTeamAgent):
    def __init__(self, config: BiographyConfig, interview_session: 'InterviewSession'):
        super().__init__(
            name="SessionSummaryManager",
            description="Prepares end-of-session summaries and next session questions based on new memories and follow-up questions",
            config=config,
            interview_session=interview_session
        )
        self.session_note = self.interview_session.session_note
        
        self.tools = {
            "update_last_meeting_summary": UpdateLastMeetingSummary(session_note=self.session_note),
            "update_user_portrait": UpdateUserPortrait(session_note=self.session_note),
            "add_interview_question": AddInterviewQuestion(session_note=self.session_note)
        }
        
    async def update_session_note(self, new_memories: List[Dict], follow_up_questions: List[Dict]):
        """Update session notes with new memories and follow-up questions."""
        prompt = self._create_session_note_prompt(
            new_memories=new_memories,
            follow_up_questions=follow_up_questions
        )
        self.add_event(sender=self.name, tag="prompt", content=prompt)
        response = self.call_engine(prompt)
        self.add_event(sender=self.name, tag="llm_response", content=response)
        
        # Handle the tool calls
        try:
            self.handle_tool_calls(response)
            self.add_event(
                sender=self.name,
                tag="event_result",
                content="Successfully updated session notes"
            )
        except Exception as e:
            error_msg = f"Error updating session notes: {str(e)}\nResponse: {response}"
            self.add_event(sender=self.name, tag="error", content=error_msg)
            raise

    def _create_session_note_prompt(self, new_memories: List[Dict], follow_up_questions: List[Dict]) -> str:
        return SESSION_NOTE_AGENT_PROMPT.format(
            user_portrait=self.session_note.get_user_portrait_str(),
            last_meeting_summary=self.session_note.get_last_meeting_summary_str(),
            questions_and_notes=self.session_note.get_questions_and_notes_str(hide_answered="a"),
            new_memories="\n".join([f"- {m['text']}" for m in new_memories]),
            follow_up_questions="\n".join([
                "<question>\n"
                f"<content>{q['content']}</content>\n"
                f"<context>{q['context']}</context>\n" 
                "</question>"
                for q in follow_up_questions
            ]),
            tool_descriptions=self.get_tools_description()
        )

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
    topic: str = Field(description="The topic category for the question")
    question: str = Field(description="The actual question text")
    question_id: str = Field(description="The ID for the question (e.g., '1', '1.1', etc.)")
    is_parent: bool = Field(description="Whether this is a parent question")
    parent_id: Optional[str] = Field(description="The ID of the parent question if this is a sub-question", default=None)
    parent_text: Optional[str] = Field(description="The text of the parent question if this is a sub-question", default=None)

class AddInterviewQuestion(BaseTool):
    """Tool for adding new interview questions."""
    name: str = "add_interview_question"
    description: str = (
        "Adds a new interview question to the session notes. "
        "For parent questions, set is_parent=True and leave parent_id/parent_text empty. "
        "For sub-questions, set is_parent=False and provide both parent_id and parent_text "
        "to help maintain context when generating follow-up questions."
    )
    args_schema: Type[BaseModel] = AddInterviewQuestionInput
    session_note: SessionNote = Field(...)

    def _run(
        self,
        topic: str,
        question: str,
        question_id: str,
        is_parent: bool,
        parent_id: Optional[str] = None,
        parent_text: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            question_id = str(question_id)
            parent_id = str(parent_id)

            self.session_note.add_interview_question(
                topic=str(topic),
                question=str(question).strip(),
                question_id=question_id
            )
            
            if is_parent:
                return f"Added parent question {question_id} to topic {topic}"
            else:
                return f"Added sub-question {question_id} under parent {parent_id}: '{parent_text}'"
        except Exception as e:
            raise ToolException(f"Error adding interview question: {str(e)}")