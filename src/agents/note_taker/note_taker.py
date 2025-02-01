# Python standard library imports
from typing import Dict, Type, Optional, List, TYPE_CHECKING, TypedDict
import os
from dotenv import load_dotenv
import asyncio
from datetime import datetime
import concurrent.futures
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
from utils.logger import SessionLogger

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession

load_dotenv()

class NoteTakerConfig(TypedDict, total=False):
    """Configuration for the NoteTaker agent."""
    user_id: str

class NoteTaker(BaseAgent, Participant):
    def __init__(self, config: NoteTakerConfig, interview_session: 'InterviewSession'):
        BaseAgent.__init__(
            self,name="NoteTaker",
            description="Agent that takes notes and manages the user's memory bank",
            config=config
        )
        Participant.__init__(self, title="NoteTaker", interview_session=interview_session)
        
        self.user_id = config.get("user_id")
        self.max_events_len = int(os.getenv("MAX_EVENTS_LEN", 40))
        self.max_consideration_iterations = int(os.getenv("MAX_CONSIDERATION_ITERATIONS", 3))

        self.new_memories = []  # Track new memories added in current session
        self._notes_lock = asyncio.Lock()  # Lock for write_session_notes
        self._memory_lock = asyncio.Lock()  # Lock for update_memory_bank
        
        self.tools = {
            "update_memory_bank": UpdateMemoryBank(
                memory_bank=self.interview_session.memory_bank,
                note_taker=self
            ),
            "update_session_note": UpdateSessionNote(session_note=self.interview_session.session_note),
            "add_interview_question": AddInterviewQuestion(session_note=self.interview_session.session_note),
            "recall": Recall(memory_bank=self.interview_session.memory_bank),
            "decide_followups": DecideFollowups()
        }
        
    async def on_message(self, message: Message):
        '''This function is called when the user or interviewer sends a message and updates the shared chat history of the interview session.'''
        # Add event without lock since it's thread-safe
        print(f"[{datetime.now()}] {message.role}: {message.content}")
        self.add_event(sender=message.role, tag="message", content=message.content)
        
        if message.role == "User":
            # Create background task instead of awaiting
            asyncio.create_task(self._process_user_message())

    async def _process_user_message(self):
        # Run both updates concurrently, each with their own lock
        print(f"[{datetime.now()}] {self.name}: Processing user message")
        # Create thread pool for parallel execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, lambda: asyncio.run(self._locked_write_session_notes())),
                loop.run_in_executor(executor, lambda: asyncio.run(self._locked_update_memory_bank()))
            ]
            await asyncio.gather(*tasks)
        

    async def _locked_write_session_notes(self) -> None:
        """Wrapper to handle write_session_notes with lock"""
        print(f"[{datetime.now()}] {self.name}: Writing session notes")
        async with self._notes_lock:
            await self.write_session_notes()

    async def _locked_update_memory_bank(self) -> None:
        """Wrapper to handle update_memory_bank with lock"""
        print(f"[{datetime.now()}] {self.name}: Updating memory bank")
        async with self._memory_lock:
            await self.update_memory_bank()

    async def write_session_notes(self) -> None:
        """Process user's response by updating session notes and considering follow-up questions."""
        # First update the direct response in session notes
        await self.update_session_note()
        
        # Then consider if we need follow-up questions
        await self.consider_followups()

    async def consider_followups(self) -> None:
        """Determine if follow-up questions should be proposed based on the conversation context."""
        iterations = 0

        while iterations < self.max_consideration_iterations:
            ## Decide if we need to propose follow-ups + propose follow-ups if needed
            prompt = self._get_formatted_prompt("consider_followups")
            self.add_event(sender=self.name, tag="consider_followups_prompt", content=prompt)

            # Call the LLM engine with the prompt to determine whether a follow-up should be proposed
            tool_call = await self.call_engine_async(prompt)
            self.add_event(sender=self.name, tag="consider_followups_response", content=tool_call)
            
            # Handle tool calls in the response
            tool_responses = self.handle_tool_calls(tool_call)

            if "decide_followups" in tool_call:
                if "yes" in tool_responses:
                    # Propose follow-up question and leave the loop
                    self.add_event(sender=self.name, tag="decide_propose_followups", content=tool_responses)
                    await self.propose_followups()
                break
            elif "recall" in tool_call:
                # Get recall response and confidence level
                self.add_event(sender=self.name, tag="recall_response", content=tool_responses)

            # Consider proposing follow-ups again
            iterations += 1
        
        if iterations >= self.max_consideration_iterations:
            self.add_event(
                sender="system",
                tag="error",
                content=f"Exceeded maximum number of consideration iterations ({self.max_consideration_iterations})"
            )

    async def propose_followups(self) -> None:
        """Propose follow-up questions based on the user's recent answers. Draws from the prompts in note_taker/prompts.py"""
        prompt = self._get_formatted_prompt("propose_followups")
        self.add_event(sender=self.name, tag="propose_followups_prompt", content=prompt)
        response = await self.call_engine_async(prompt)
        self.add_event(sender=self.name, tag="propose_followups_response", content=response)
        self.handle_tool_calls(response)
        SessionLogger.log_to_file("chat_history", f"[PROPOSE_FOLLOWUPS]\n{response}")
        SessionLogger.log_to_file("chat_history", f"{self.interview_session.session_note.visualize_topics()}")

    async def update_memory_bank(self) -> None:
        """Process the latest conversation and update the memory bank if needed."""
        prompt = self._get_formatted_prompt("update_memory_bank")
        self.add_event(sender=self.name, tag="update_memory_bank_prompt", content=prompt)
        response = await self.call_engine_async(prompt)
        self.add_event(sender=self.name, tag="update_memory_bank_response", content=response)
        self.handle_tool_calls(response)
        self.interview_session.memory_bank.save_to_file(self.user_id)

    async def update_session_note(self) -> None:
        prompt = self._get_formatted_prompt("update_session_note")
        self.add_event(sender=self.name, tag="update_session_note_prompt", content=prompt)
        response = await self.call_engine_async(prompt)
        self.add_event(sender=self.name, tag="update_session_note_response", content=response)
        self.handle_tool_calls(response)
    
    def _get_formatted_prompt(self, prompt_type: str) -> str:
        '''Gets the formatted prompt for the NoteTaker agent.
        
        Args:
            prompt_type: The type of prompt to get.
        '''
        prompt = get_prompt(prompt_type)
        if prompt_type in ["consider_followups", "propose_followups"]:
            events = self.get_event_stream_str(filter=[
                {"tag": "message"},
                {"tag": "decide_propose_followups"},
                {"sender": self.name, "tag": "recall_response"},
            ], as_list=True)
            
            recent_events = events[-self.max_events_len:] if len(events) > self.max_events_len else events
            
            return format_prompt(prompt, {
                "event_stream": "\n".join(recent_events),
                "questions_and_notes": self.interview_session.session_note.get_questions_and_notes_str(),
                "tool_descriptions": self.get_tools_description(
                    selected_tools=["recall", "decide_followups"] if prompt_type == "consider_followups" else ["add_interview_question"]
                )
            })
        elif prompt_type == "update_memory_bank":
            events = self.get_event_stream_str(filter=[
                {"tag": "message"}, 
                {"sender": self.name, "tag": "update_memory_bank_response"},
            ], as_list=True)
            
            recent_events = events[-self.max_events_len:] if len(events) > self.max_events_len else events
            
            return format_prompt(prompt, {
                "event_stream": "\n".join(recent_events),
                "tool_descriptions": self.get_tools_description(selected_tools=["update_memory_bank"])
            })
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
            
    def add_new_memory(self, memory: Dict):
        """Track newly added memory"""
        self.new_memories.append(memory)

    def get_session_memories(self) -> List[Dict]:
        """Get all memories added during current session"""
        return self.new_memories

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

class AddInterviewQuestionInput(BaseModel):
    topic: str = Field(description="The topic under which to add the question")
    question: str = Field(description="The interview question to add")
    question_id: str = Field(description="The ID for the question (e.g., '1', '1.1', '2.3', etc.)")
    parent_id: str = Field(description="The ID of the parent question (e.g., '1', '2', etc.). Still include it but leave it empty if it is a top-level question.")
    parent_text: str = Field(description="The text of the parent question. Still include it but leave it empty if it is a top-level question.")

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
            ## TODO: pruning (add timestamp)
            self.session_note.add_interview_question(
                topic=topic,
                question=question,
                question_id=str(question_id)
            )
            self.session_note.save() ## TODO: might be redundant
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

class RecallInput(BaseModel):
    query: str = Field(description="The query to search for in the memory bank")
    reasoning: str = Field(description="Explain: "
                          "0. The current confidence level (1-10) "
                          "1. Why you need this specific information "
                          "2. How the results will help determine follow-up questions")

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

class DecideFollowupsInput(BaseModel):
    decision: str = Field(
        description="Your decision about whether to propose follow-ups (yes or no)",
        pattern="^(yes|no)$"
    )
    reasoning: str = Field(description="Brief explanation of your decision based on the recall results with confidence score (1-10). If yes, explain what kind of follow-ups to propose.")

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