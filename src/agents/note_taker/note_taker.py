# Python standard library imports
from typing import Dict, Type, Optional, List, TYPE_CHECKING, TypedDict

# Third-party imports
from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException
from pydantic import BaseModel, Field

# Local imports
from agents.base_agent import BaseAgent
from agents.note_taker.prompts import get_prompt
from agents.prompt_utils import format_prompt
from interview_session.session_models import Participant, Message
from memory_bank.memory_bank_vector_db import MemoryBank
from session_note.session_note import SessionNote

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession

class NoteTakerConfig(TypedDict, total=False):
    """Configuration for the NoteTaker agent."""
    user_id: str
    followup_interval: int  # Number of turns between follow-ups

class NoteTaker(BaseAgent, Participant):
    def __init__(self, config: NoteTakerConfig, interview_session: 'InterviewSession'):
        BaseAgent.__init__(
            self,name="NoteTaker",
            description="Agent that takes notes and manages the user's memory bank",
            config=config
        )
        Participant.__init__(self, title="NoteTaker", interview_session=interview_session)
        
        self.user_id = config.get("user_id")
        self.memory_bank = MemoryBank.load_from_file(self.user_id)
        self.new_memories = []  # Track new memories added in current session
        self.message_count = 0  # Counter for messages since last follow-up
        self.followup_interval = config.get("followup_interval", 3)  # Number of turns between follow-ups
        
        self.tools = {
            "update_memory_bank": UpdateMemoryBank(memory_bank=self.memory_bank, note_taker=self),
            "update_session_note": UpdateSessionNote(session_note=self.interview_session.session_note),
            "add_interview_question": AddInterviewQuestion(session_note=self.interview_session.session_note)
        }
        
    async def on_message(self, message: Message):
        self.add_event(sender=message.role, tag="message", content=message.content)
        if message.role == "User":
            self.update_session_note()
            self.update_memory_bank()
            
            # Increment counter and check if it's time to propose follow-ups
            self.message_count += 1
            if self.message_count >= self.followup_interval:
                self.propose_followups()
                self.message_count = 0
    
    def propose_followups(self) -> None:
        """Propose follow-up questions based on the user's recent answers."""
        prompt = self.get_formatted_prompt("propose_followups")
        self.add_event(sender=self.name, tag="propose_followups_prompt", content=prompt)
        response = self.call_engine(prompt)
        self.add_event(sender=self.name, tag="llm_response", content=response)
        self.handle_tool_calls(response)

    def update_memory_bank(self) -> None:
        """Process the latest conversation and update the memory bank if needed."""
        prompt = self.get_formatted_prompt("update_memory_bank")
        self.add_event(sender=self.name, tag="update_memory_bank_prompt", content=prompt)
        response = self.call_engine(prompt)
        self.add_event(sender=self.name, tag="llm_response", content=response)
        self.add_event(sender=self.name, tag="update_memory_bank", content=response)
        self.handle_tool_calls(response)
        self.memory_bank.save_to_file(self.user_id)

    def update_session_note(self) -> None:
        prompt = self.get_formatted_prompt("update_session_note")
        self.add_event(sender=self.name, tag="update_session_note_prompt", content=prompt)
        response = self.call_engine(prompt)
        self.add_event(sender=self.name, tag="llm_response", content=response)
        self.add_event(sender=self.name, tag="update_session_note", content=response)
        self.handle_tool_calls(response)
    
    def get_formatted_prompt(self, prompt_type: str) -> str:
        prompt = get_prompt(prompt_type)
        if prompt_type == "update_memory_bank":
            event_stream = self.get_event_stream_str(filter=[{"tag": "message"}, 
                                                            {"sender": self.name, "tag": "update_memory_bank"},
                                                            {"sender": "system", "tag": "update_memory_bank"}])
            return format_prompt(prompt, {"event_stream": event_stream,
                                         "tool_descriptions": self.get_tools_description(selected_tools=["update_memory_bank"])})
        elif prompt_type == "update_session_note":
            events = self.get_event_stream_str(filter=[{"tag": "message"}], as_list=True)
            current_qa = events[-2:] if len(events) >= 2 else []
            previous_events = events[:-2] if len(events) >= 2 else events
            
            return format_prompt(prompt, {
                "previous_events": "\n".join(previous_events),
                "current_qa": "\n".join(current_qa),
                "questions_and_notes": self.interview_session.session_note.get_questions_and_notes_str(hide_answered="qa"),
                "tool_descriptions": self.get_tools_description(selected_tools=["update_session_note"])
            })
        elif prompt_type == "propose_followups":
            # Get recent messages (2 messages per exchange: interviewer + user)
            events = self.get_event_stream_str(filter=[{"tag": "message"}], as_list=True)
            num_messages = 2 * self.followup_interval
            recent_exchanges = events[-num_messages:] if len(events) >= num_messages else events
            
            return format_prompt(prompt, {
                "event_stream": "\n".join(recent_exchanges),
                "questions_and_notes": self.interview_session.session_note.get_questions_and_notes_str(),
                "tool_descriptions": self.get_tools_description(selected_tools=["add_interview_question"])
            })
            
    def add_new_memory(self, memory: Dict):
        """Track newly added memory"""
        self.new_memories.append(memory)

    def get_session_memories(self) -> List[Dict]:
        """Get all memories added during current session"""
        return self.new_memories

class AddInterviewQuestionInput(BaseModel):
    topic: str = Field(description="The topic under which to add the question")
    question: str = Field(description="The interview question to add")
    question_id: str = Field(description="The ID for the question (e.g., '1', '1.1', '2.3', etc.)")
    parent_id: str = Field(description="The ID of the parent question (e.g., '1', '2', etc.)")
    parent_text: str = Field(description="The text of the parent question")

class UpdateMemoryBankInput(BaseModel):
    title: str = Field(description="A concise but descriptive title for the memory")
    text: str = Field(description="A clear summary of the information")
    metadata: dict = Field(description=(
        "Additional metadata about the memory. "
        "This can include topics, people mentioned, emotions, locations, dates, relationships, life events, achievements, goals, aspirations, beliefs, values, preferences, hobbies, interests, education, work experience, skills, challenges, fears, dreams, etc. "
        "Of course, you don't need to include all of these in the metadata, just the most relevant ones."
    ))
    importance_score: int = Field(description=(
        "This field represents the importance of the memory on a scale from 1 to 10. "
        "A score of 1 indicates everyday routine activities like brushing teeth or making the bed. "
        "A score of 10 indicates major life events like a relationship ending or getting accepted to college. "
        "Use this scale to rate how significant this memory is likely to be."
    ))

class UpdateMemoryBank(BaseTool):
    """Tool for updating the memory bank."""
    name: str = "update_memory_bank"
    description: str = "A tool for storing new memories in the memory bank."
    args_schema: Type[BaseModel] = UpdateMemoryBankInput
    memory_bank: MemoryBank = Field(...)
    note_taker: NoteTaker = Field(...)

    def _run(
        self,
        title: str,
        text: str,
        metadata: dict,
        importance_score: int,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            memory = self.memory_bank.add_memory(
                title=title, 
                text=text, 
                metadata=metadata, 
                importance_score=importance_score
            )
            self.note_taker.add_new_memory(memory.to_dict())
            return f"Successfully stored memory: {title}"
        except Exception as e:
            raise ToolException(f"Error storing memory: {e}")

class AddInterviewQuestion(BaseTool):
    """Tool for adding new interview questions."""
    name: str = "add_interview_question"
    description: str = "Adds a new interview question to the session notes"
    args_schema: Type[BaseModel] = AddInterviewQuestionInput
    session_note: SessionNote = Field(...)

    def _run(
        self,
        topic: str,
        question: str,
        question_id: str,
        parent_id: str,
        parent_text: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            self.session_note.add_interview_question(
                topic=topic,
                question=question,
                question_id=str(question_id)
            )
            return f"Successfully added question {question_id} as follow-up to question {parent_id}"
        except Exception as e:
            raise ToolException(f"Error adding interview question: {str(e)}")

class UpdateSessionNoteInput(BaseModel):
    question_id: str = Field(description=("The ID of the question to update. "
                                          "It can be a top-level question or a sub-question, e.g. '1' or '1.1', '2.1.2', etc. "
                                          "It can also be empty, in which case the note will be added as an additional note."))
    note: str = Field(description="A concise note to be added to the question, or as an additional note if the question_id is empty.")

class UpdateSessionNote(BaseTool):
    """Tool for updating the session note."""
    name: str = "update_session_note"
    description: str = "A tool for updating the session note."
    args_schema: Type[BaseModel] = UpdateSessionNoteInput
    session_note: SessionNote = Field(...)
    
    def _run(
        self,
        question_id: str,
        note: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        self.session_note.add_note(question_id=str(question_id), note=note)
        target_question = question_id if question_id else "additional note"
        return f"Successfully added the note for `{target_question}`."
