from typing import Dict, List, TYPE_CHECKING
from agents.biography_team.base_biography_agent import BiographyConfig, BiographyTeamAgent
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, ToolException
from typing import Type, Optional
from langchain_core.callbacks.manager import CallbackManagerForToolRun

from agents.biography_team.session_summary_writer.prompts import SESSION_SUMMARY_PROMPT, INTERVIEW_QUESTIONS_PROMPT
from memory_bank.memory_bank_vector_db import MemoryBank
from session_note.session_note import SessionNote

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession

class SessionSummaryWriter(BiographyTeamAgent):
    def __init__(self, config: BiographyConfig, interview_session: 'InterviewSession'):
        super().__init__(
            name="SessionSummaryWriter",
            description="Prepares end-of-session summaries and manages interview questions",
            config=config,
            interview_session=interview_session
        )
        self.session_note = self.interview_session.session_note
        self.max_consideration_iterations = 3
        
        # Initialize all tools
        self.tools = {
            # Summary tools
            "update_last_meeting_summary": UpdateLastMeetingSummary(session_note=self.session_note),
            "update_user_portrait": UpdateUserPortrait(session_note=self.session_note),
            
            # Question tools
            "add_interview_question": AddInterviewQuestion(session_note=self.session_note),
            "delete_interview_question": DeleteInterviewQuestion(session_note=self.session_note),
            "recall": Recall(memory_bank=self.interview_session.memory_bank)
        }
        
    async def update_session_note(self, new_memories: List[Dict], follow_up_questions: List[Dict]):
        """Update session notes with new memories and follow-up questions."""
        # First update summaries and user portrait
        await self._update_session_summary(new_memories)
        
        # Then manage interview questions
        await self._manage_interview_questions(follow_up_questions)
    
    async def _update_session_summary(self, new_memories: List[Dict]):
        """Update session summary and user portrait."""
        prompt = self._get_summary_prompt(new_memories)
        self.add_event(sender=self.name, tag="summary_prompt", content=prompt)
        
        response = self.call_engine(prompt)
        self.add_event(sender=self.name, tag="summary_response", content=response)
        
        self.handle_tool_calls(response)
    
    async def _manage_interview_questions(self, follow_up_questions: List[Dict]):
        """Manage interview questions based on existing information.
        
        Will iterate up to max_consideration_iterations times:
        - Each iteration either does memory search or takes actions
        - Breaks when actions are taken or max iterations reached
        """
        iterations = 0
        
        while iterations < self.max_consideration_iterations:
            prompt = self._get_questions_prompt(follow_up_questions)
            self.add_event(sender=self.name, tag="questions_prompt", content=prompt)
            
            tool_calls = self.call_engine(prompt)
            self.add_event(sender=self.name, tag="questions_response", content=tool_calls)
            
            try:
                # Check if this is a recall or action response
                is_recall = "<recall>" in tool_calls and not any(tag in tool_calls for tag in ["<delete_interview_question>", "<add_interview_question>"])
                
                tool_response = self.handle_tool_calls(tool_calls)
                
                if is_recall:
                    # If it's a recall, add the response to events and continue
                    self.add_event(
                        sender=self.name,
                        tag="recall_response",
                        content=tool_response
                    )
                    iterations += 1
                else:
                    # If it's actions, log success and break
                    self.add_event(
                        sender=self.name,
                        tag="question_actions",
                        content="Successfully updated interview questions"
                    )
                    break
                    
            except Exception as e:
                error_msg = f"Error managing interview questions: {str(e)}\nResponse: {tool_calls}"
                self.add_event(sender=self.name, tag="error", content=error_msg)
                raise
        
        if iterations >= self.max_consideration_iterations:
            self.add_event(
                sender=self.name,
                tag="warning",
                content=f"Reached maximum iterations ({self.max_consideration_iterations}) without taking actions"
            )
    
    def _get_summary_prompt(self, new_memories: List[Dict]) -> str:
        summary_tool_names = ["update_last_meeting_summary", "update_user_portrait"]
        return SESSION_SUMMARY_PROMPT.format(
            new_memories="\n".join([f"- {m['text']}" for m in new_memories]),
            user_portrait=self.session_note.get_user_portrait_str(),
            tool_descriptions=self.get_tools_description(summary_tool_names)
        )
    
    def _get_questions_prompt(self, follow_up_questions: List[Dict]) -> str:
        question_tool_names = ["add_interview_question", "delete_interview_question", "recall"]
        events = self.get_event_stream_str(
            filter=[
                {"sender": self.name, "tag": "recall_response"}
            ],
            as_list=True
        )
        
        return INTERVIEW_QUESTIONS_PROMPT.format(
            questions_and_notes=self.session_note.get_questions_and_notes_str(),
            follow_up_questions="\n\n".join([
                "<question>\n"
                f"<content>{q['content']}</content>\n"
                f"<context>{q['context']}</context>\n"
                "</question>"
                for q in follow_up_questions
            ]),
            event_stream="\n".join(events[-10:]),
            tool_descriptions=self.get_tools_description(question_tool_names)
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
    topic: str = Field(description="The topic category for the question (e.g., 'Career', 'Education')")
    question: str = Field(description="The actual question text")
    question_id: str = Field(description="The ID for the question (e.g., '1', '1.1', '2.3')")
    is_parent: bool = Field(description="Whether this is a parent question (true) or sub-question (false)")
    parent_id: Optional[str] = Field(
        description="Required for sub-questions: ID of the parent question",
        default=None
    )
    parent_text: Optional[str] = Field(
        description="Required for sub-questions: Text of the parent question for context",
        default=None
    )

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
        parent_id: str,
        parent_text: str,
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
            
            return f"Added parent question {question_id} as follow-up to question {parent_id}"
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
    query: str = Field(
        description="The search query to find relevant information. Make it broad enough to cover related topics."
    )
    reasoning: str = Field(
        description="Explain:\n"
        "1. What information you're looking for\n"
        "2. How this search will help evaluate multiple related questions\n"
        "3. What decisions this search will inform"
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
    memory_bank: MemoryBank = Field(...)

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
<reasoning>{reasoning}</reasoning>
<results>
{memories_str}
</results>
</memory_search>
""" if memories_str else f"""\
<memory_search>
<query>{query}</query>
<reasoning>{reasoning}</reasoning>
<results>No relevant memories found.</results>
</memory_search>"""
        except Exception as e:
            raise ToolException(f"Error recalling memories: {e}")