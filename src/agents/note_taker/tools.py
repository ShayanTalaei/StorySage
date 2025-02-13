from typing import Type, Optional, List, Callable, Dict


from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException
from pydantic import BaseModel, Field, SkipValidation

from content.memory_bank.memory_bank_base import MemoryBankBase
from content.session_note.session_note import SessionNote
from content.question_bank.question_bank_base import QuestionBankBase

class AddInterviewQuestionInput(BaseModel):
    topic: str = Field(description="The topic under which to add the question")
    question: str = Field(description="The interview question to add")
    question_id: str = Field(
        description="The ID for the question (e.g., '1', '1.1', '2.3', etc.)")
    parent_id: str = Field(
        description="The ID of the parent question (e.g., '1', '2', etc.). Still include it but leave it empty if it is a top-level question.")
    parent_text: str = Field(
        description="The text of the parent question. Still include it but leave it empty if it is a top-level question.")


class AddInterviewQuestion(BaseTool):
    """Tool for adding new interview questions."""
    name: str = "add_interview_question"
    description: str = "Adds a new interview question to the session notes"
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
            # TODO: pruning (add timestamp)
            self.session_note.add_interview_question(
                topic=topic,
                question=question,
                question_id=str(question_id)
            )
            self.session_note.save()
            return f"Successfully added question {question_id} as follow-up to question {parent_id}"
        except Exception as e:
            raise ToolException(f"Error adding interview question: {str(e)}")


class UpdateSessionNoteInput(BaseModel):
    question_id: str = Field(description=("The ID of the question to update. "
                                          "It can be a top-level question or a sub-question, e.g. '1' or '1.1', '2.1.2', etc. "
                                          "It can also be empty, in which case the note will be added as an additional note."))
    note: str = Field(
        description="A concise note to be added to the question, or as an additional note if the question_id is empty.")


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


class RecallInput(BaseModel):
    reasoning: str = Field(description="Explain: "
                           "0. The current confidence level (1-10) "
                           "1. Why you need this specific information "
                           "2. How the results will help determine follow-up questions")
    query: str = Field(
        description="The query to search for in the memory bank")


class Recall(BaseTool):
    """Tool for recalling memories."""
    name: str = "recall"
    description: str = (
        "A tool for recalling memories. "
        "Use this tool to check if we already have relevant information about a topic "
        "before deciding to propose follow-up questions. "
        "Explain your search intent and how the results will guide your decision."
    )
    args_schema: Type[BaseModel] = RecallInput
    memory_bank: MemoryBankBase = Field(...)  # Changed to use base class

    def _run(
        self,
        query: str,
        reasoning: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            memories = self.memory_bank.search_memories(query)
            memories_str = "\n".join(
                [f"<memory>{memory['text']}</memory>" for memory in memories])
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


class UpdateMemoryBankInput(BaseModel):
    temp_id: str = Field(description="Unique temporary ID for this memory (e.g., MEM_TEMP_1)")
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
    # source_interview_response: str = Field(description=(
    #     "The original user response from the interview that this memory is derived from. "
    #     "This should be the exact message from the user that contains this information."
    # ))


class UpdateMemoryBank(BaseTool):
    """Tool for updating the memory bank."""
    name: str = "update_memory_bank"
    description: str = "A tool for storing new memories in the memory bank."
    args_schema: Type[BaseModel] = UpdateMemoryBankInput
    memory_bank: MemoryBankBase = Field(...)
    on_memory_added: SkipValidation[Callable[[Dict], None]] = Field(...)
    update_memory_map: SkipValidation[Callable[[str, str], None]] = Field(
        description="Callback function to update the memory ID mapping"
    )
    get_current_response: SkipValidation[Callable[[], str]] = Field(
        description="Function to get the current user response"
    )

    def _run(
        self,
        temp_id: str,
        title: str,
        text: str,
        metadata: dict,
        importance_score: int,
        # source_interview_response: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            memory = self.memory_bank.add_memory(
                title=title, 
                text=text, 
                metadata=metadata, 
                importance_score=importance_score,
                source_interview_response=self.get_current_response()
            )
            
            # Use callback to update the mapping
            self.update_memory_map(temp_id, memory.id)
            
            # Trigger callback to track newly added memory
            self.on_memory_added(memory.to_dict())
                
            return f"Successfully stored memory: {title}"
        except Exception as e:
            raise ToolException(f"Error storing memory: {e}")


class AddHistoricalQuestionInput(BaseModel):
    content: str = Field(description="The question text to add")
    temp_memory_ids: List[str] = Field(
        description="List of temporary memory IDs that are relevant to this question. "
        "These should match the temporary IDs used in update_memory_bank calls. "
        "Format: MEM_TEMP_1,MEM_TEMP_2 (comma-separated, no brackets)",
        default=[]
    )


class AddHistoricalQuestion(BaseTool):
    """Tool for adding historical questions to the question bank."""
    name: str = "add_historical_question"
    description: str = (
        "A tool for storing questions that were asked in the interview. "
        "Use this when saving a question that has been asked, "
        "along with any memories that contain information relevant to this question."
    )
    args_schema: Type[BaseModel] = AddHistoricalQuestionInput
    question_bank: QuestionBankBase = Field(...)
    memory_bank: MemoryBankBase = Field(...)
    get_real_memory_ids: SkipValidation[Callable[[List[str]], List[str]]] = Field(
        description="Callback function to get real memory IDs from temporary IDs"
    )

    def _run(
        self,
        content: str,
        temp_memory_ids: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            # Parse comma-separated string into list
            temp_ids = [id.strip() for id in temp_memory_ids.split(",") if id.strip()]
            
            # Get real memory IDs through callback
            real_memory_ids = self.get_real_memory_ids(temp_ids)
            
            # Link the question to memories
            question = self.question_bank.add_question(
                content=content,
                memory_ids=real_memory_ids
            )
            
            # Link memories to the question
            for memory_id in real_memory_ids:
                self.memory_bank.link_question(memory_id, question.id)
            
            return f"Successfully stored question: {content}"
        except Exception as e:
            raise ToolException(f"Error storing question: {e}")