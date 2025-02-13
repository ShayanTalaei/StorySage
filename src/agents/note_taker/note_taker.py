# Python standard library imports
from typing import Dict, List, TYPE_CHECKING, TypedDict
import os
from dotenv import load_dotenv
import asyncio
from datetime import datetime


from agents.base_agent import BaseAgent
from agents.interviewer.interviewer import Recall
from agents.note_taker.prompts import get_prompt
from agents.note_taker.tools import AddInterviewQuestion, UpdateSessionNote, UpdateMemoryBank, AddHistoricalQuestion
from utils.llm.prompt_utils import format_prompt
from interview_session.session_models import Participant, Message
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
        
        # Config variables
        self.user_id = config.get("user_id")
        self.max_events_len = int(os.getenv("MAX_EVENTS_LEN", 40))
        self.max_consideration_iterations = int(os.getenv("MAX_CONSIDERATION_ITERATIONS", 3))

        # New memories added in current session
        self.new_memories = []  
        # Mapping from temporary memory IDs to real IDs
        self.memory_id_map = {}

        # Locks and processing flags
        self._notes_lock = asyncio.Lock()   # Lock for write_notes_and_questions
        self._memory_lock = asyncio.Lock()  # Lock for update_memory_bank
        self.processing_in_progress = False # If processing is in progress
                
        self.tools = {
            "update_memory_bank": UpdateMemoryBank(
                memory_bank=self.interview_session.memory_bank,
                on_memory_added=self.add_new_memory,
                update_memory_map=self.update_memory_map
            ),
            "add_historical_question": AddHistoricalQuestion(
                question_bank=self.interview_session.question_bank,
                memory_bank=self.interview_session.memory_bank,
                get_real_memory_ids=self.get_real_memory_ids
            ),
            "update_session_note": UpdateSessionNote(session_note=self.interview_session.session_note),
            "add_interview_question": AddInterviewQuestion(session_note=self.interview_session.session_note),
            "recall": Recall(memory_bank=self.interview_session.memory_bank),
        }
            
    async def on_message(self, message: Message):
        '''Handle incoming messages'''
        
        self.add_event(sender=message.role, tag="message", content=message.content)
        
        if message.role == "User":
            print(f"{datetime.now()} ✅ Note taker received message from {message.role}")
            asyncio.create_task(self._process_user_message())

    async def _process_user_message(self):
        self.processing_in_progress = True
        try:
            # Run both updates concurrently, each with their own lock
            await asyncio.gather(
                self._locked_write_notes_and_questions(),
                self._locked_write_memory_and_question_bank()
            )
        finally:
            self.processing_in_progress = False

    async def _locked_write_notes_and_questions(self) -> None:
        """Wrapper to handle write_notes_and_questions with lock"""
        async with self._notes_lock:
            await self.write_notes_and_questions()

    async def _locked_write_memory_and_question_bank(self) -> None:
        """Wrapper to handle update_memory_bank with lock"""
        async with self._memory_lock:
            await self.write_memory_and_question_bank()

    async def write_notes_and_questions(self) -> None:
        """Process user's response by updating session notes and considering follow-up questions."""
        # First update the direct response in session notes
        await self.update_session_note()
        
        # Then consider and propose follow-up questions if appropriate
        await self.consider_and_propose_followups()

    async def consider_and_propose_followups(self) -> None:
        """Determine if follow-up questions should be proposed and propose them if appropriate."""
        # Get prompt for considering and proposing followups

        iterations = 0
        while iterations < self.max_consideration_iterations:
            ## Decide if we need to propose follow-ups + propose follow-ups if needed
            prompt = self._get_formatted_prompt("consider_and_propose_followups")
            self.add_event(sender=self.name, tag="consider_and_propose_followups_prompt", content=prompt)

            tool_call = await self.call_engine_async(prompt)
            self.add_event(sender=self.name, tag="consider_and_propose_followups_response", content=tool_call)

            tool_responses = self.handle_tool_calls(tool_call)

            if "add_interview_question" in tool_call:
                SessionLogger.log_to_file("chat_history", f"[PROPOSE_FOLLOWUPS]\n{tool_call}")
                SessionLogger.log_to_file("chat_history", f"{self.interview_session.session_note.visualize_topics()}")
                break
            elif "recall" in tool_call:
                # Get recall response and confidence level
                self.add_event(sender=self.name, tag="recall_response", content=tool_responses)
            else:
                break
            iterations += 1
        
        if iterations >= self.max_consideration_iterations:
            self.add_event(
                sender="system",
                tag="error",
                content=f"Exceeded maximum number of consideration iterations ({self.max_consideration_iterations})"
            )

    async def write_memory_and_question_bank(self) -> None:
        """Process the latest conversation and update both memory and question banks."""
        prompt = self._get_formatted_prompt("update_memory_question_bank")
        self.add_event(sender=self.name, tag="update_memory_question_bank_prompt", content=prompt)
        response = await self.call_engine_async(prompt)
        self.add_event(sender=self.name, tag="update_memory_question_bank_response", content=response)
        self.handle_tool_calls(response)

    async def update_session_note(self) -> None:
        prompt = self._get_formatted_prompt("update_session_note")
        self.add_event(sender=self.name, tag="update_session_note_prompt", content=prompt)
        response = await self.call_engine_async(prompt)
        self.add_event(sender=self.name, tag="update_session_note_response", content=response)
        self.handle_tool_calls(response)
    
    def _get_formatted_prompt(self, prompt_type: str) -> str:
        '''Gets the formatted prompt for the NoteTaker agent.'''
        prompt = get_prompt(prompt_type)
        if prompt_type == "consider_and_propose_followups":
            # Get all message events
            events = self.get_event_stream_str(filter=[
                {"tag": "message"},
                {"sender": self.name, "tag": "recall_response"},
            ], as_list=True)
            
            recent_events = events[-self.max_events_len:] if len(events) > self.max_events_len else events
            
            return format_prompt(prompt, {
                "event_stream": "\n".join(recent_events),
                "questions_and_notes": self.interview_session.session_note.get_questions_and_notes_str(),
                "tool_descriptions": self.get_tools_description(
                    selected_tools=["recall", "add_interview_question"]
                )
            })
        elif prompt_type == "update_memory_question_bank":
            events = self.get_event_stream_str(filter=[
                {"tag": "message"}, 
            ], as_list=True)
            current_qa = events[-2:] if len(events) >= 2 else []
            previous_events = events[:-2] if len(events) >= 2 else events
            
            if len(previous_events) > self.max_events_len:
                previous_events = previous_events[-self.max_events_len:]
            
            return format_prompt(prompt, {
                "previous_events": "\n".join(previous_events),
                "current_qa": "\n".join(current_qa),
                "tool_descriptions": self.get_tools_description(
                    selected_tools=["update_memory_bank", "add_historical_question"]
                )
            })
        elif prompt_type == "update_session_note":
            events = self.get_event_stream_str(filter=[{"tag": "message"}], as_list=True)
            current_qa = events[-2:] if len(events) >= 2 else []
            previous_events = events[:-2] if len(events) >= 2 else events
            
            if len(previous_events) > self.max_events_len:
                previous_events = previous_events[-self.max_events_len:]
            
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

    def update_memory_map(self, temp_id: str, real_id: str) -> None:
        """Callback to update the memory ID mapping"""
        self.memory_id_map[temp_id] = real_id
        SessionLogger.log_to_file("execution_log", 
            f"[MEMORY_MAP] Updated mapping {temp_id} -> {real_id}")

    def get_real_memory_ids(self, temp_ids: List[str]) -> List[str]:
        """Callback to get real memory IDs from temporary IDs"""
        real_ids = [
            self.memory_id_map[temp_id]
            for temp_id in temp_ids
            if temp_id in self.memory_id_map
        ]
        SessionLogger.log_to_file("execution_log", 
            f"[MEMORY_MAP] Converted temp IDs {temp_ids} to real IDs {real_ids}")
        return real_ids

