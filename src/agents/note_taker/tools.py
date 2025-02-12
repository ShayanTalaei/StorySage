from typing import Type, Optional


from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException
from pydantic import BaseModel, Field

from content.memory_bank.memory_bank_base import MemoryBankBase
from content.session_note.session_note import SessionNote


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


class DecideFollowupsInput(BaseModel):
    decision: str = Field(
        description="Your decision about whether to propose follow-ups (yes or no)",
        pattern="^(yes|no)$"
    )
    reasoning: str = Field(
        description="Brief explanation of your decision based on the recall results with confidence score (1-10). If yes, explain what kind of follow-ups to propose.")


class DecideFollowups(BaseTool):
    """Tool for making the final decision about proposing follow-ups."""
    name: str = "decide_followups"
    description: str = (
        "Use this tool to make your final decision about whether to propose follow-up questions "
        "after you have gathered enough information through recall searches. "
        "Provide your decision (yes/no) and explain your reasoning based on the recall results."
    )
    args_schema: Type[BaseModel] = DecideFollowupsInput

    def _run(
        self,
        decision: str,
        reasoning: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        return f"""\
<propose_followups_decision>
<decision>{decision}</decision>
<reasoning>{reasoning}</reasoning>
</propose_followups_decision>"""
