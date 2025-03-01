from typing import Dict, List, TYPE_CHECKING, Optional
import asyncio
from dotenv import load_dotenv
import logging

from agents.biography_team.base_biography_agent import BiographyConfig
from agents.biography_team.planner.planner import BiographyPlanner
from agents.biography_team.section_writer.section_writer import SectionWriter
from agents.biography_team.session_summary_writer.session_summary_writer import SessionSummaryWriter
from agents.biography_team.models import Plan
from content.memory_bank.memory import Memory
from utils.logger.session_logger import setup_default_logger, SessionLogger


if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession

load_dotenv()


class BiographyOrchestrator:
    def __init__(self, config: BiographyConfig, interview_session: Optional['InterviewSession']):
        # Planning and writing agents
        self._planner = BiographyPlanner(config, interview_session)
        self._section_writer = SectionWriter(config, interview_session)

        # Session note agent if it is an post-interview update
        if interview_session:
            self._session_summary_writer = SessionSummaryWriter(
                config, interview_session)
            self._interview_session = interview_session
        else:
            # Setup logging for non-interview operations
            setup_default_logger(
                user_id=config.get("user_id"),
                log_type="user_edits",
                log_level=logging.INFO
            )

        # Flags to track different types of updates in progress
        self.biography_update_in_progress = False
        self.session_note_update_in_progress = False
        
        # Lock for biography updates to ensure only one runs at a time
        self._biography_update_lock = asyncio.Lock()

    async def _process_section_update(self, item: Plan) -> None:
        """Process a single section update."""
        try:
            result = await self._section_writer.update_section(item)
            item.status = "completed" if result.success else "failed"
        except Exception as e:
            item.status = "failed"
            item.error = str(e)

    async def _process_updates_in_batches(self, items: List[Plan]) -> None:
        """Process todo items concurrently using asyncio."""
        pending_items = [item for item in items if item.status == "pending"]
        
        # Create tasks for concurrent execution
        tasks = []
        for item in pending_items:
            item.status = "in_progress"
            task = asyncio.create_task(self._process_section_update(item))
            tasks.append(task)
        
        # Wait for all tasks to complete
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logging.error(f"Error processing updates: {str(e)}")

    async def update_biography_with_memories(self, new_memories: List[Memory], is_auto_update: bool = False):
        """Handle the biography content updates (planner and section writer)"""
        if not new_memories:
            return
        
        # Acquire lock to ensure only one update runs at a time
        async with self._biography_update_lock:
            try:
                self.biography_update_in_progress = True
                
                # 1. Get plans from planner
                plans = await \
                    self._planner.create_adding_new_memory_plans(new_memories)
                SessionLogger.log_to_file("execution_log", 
                                        f"[BIOGRAPHY] Planned updates for biography")

                # 2. Execute section updates in parallel batches
                await self._process_updates_in_batches(plans)
                SessionLogger.log_to_file("execution_log", 
                                        f"[BIOGRAPHY] Executed updates for biography")
                
                # Save biography after all updates are complete
                await \
                    self._section_writer.save_biography(is_auto_update=is_auto_update)
                
            finally:
                self.biography_update_in_progress = False

    async def update_session_note_with_memories(self):
        """Update just the session note."""
        try:
            self.session_note_update_in_progress = True
            
            # 1. Collect all follow-ups proposed in the session
            follow_up_questions = self._collect_follow_up_questions()
            
            # 2. Regenerate session note with new memories and follow-ups
            await self._session_summary_writer.regenerate_session_note(
                follow_up_questions=follow_up_questions
            )
            
        finally:
            self.session_note_update_in_progress = False
        
    async def update_biography_and_notes(self, selected_topics: Optional[List[str]] = None):
        """Update biography with new memories."""
        try:
            # Set both flags to indicate updates are in progress
            self.biography_update_in_progress = True
            self.session_note_update_in_progress = True

            new_memories: List[Memory] = await (
                self._interview_session.get_session_memories(
                    include_processed=False
                )
            )

            if not new_memories:
                self._interview_session.session_note.save(
                    increment_session_id=True
                )
                return

            # 1. First process biography updates
            await self.update_biography_with_memories(new_memories)

            # 2. Process session note update
            session_note_task = asyncio.create_task(
                self.update_session_note_with_memories()
            )

            # If topics are provided now, set them immediately
            if selected_topics is not None:
                self._session_summary_writer.set_selected_topics(selected_topics)

            # Wait for session note task to complete
            await session_note_task

            # Save session note after all updates are complete
            self._interview_session.session_note.save(increment_session_id=True)

        finally:
            # Make sure both flags are cleared in case of errors
            self.biography_update_in_progress = False
            self.session_note_update_in_progress = False

    async def process_user_edits(self, edits: List[Dict]):
        """Process user-requested edits to the biography.
        This is used for the API mode and non-interview sessions."""
        todo_items: List[Plan] = []

        for edit in edits:
            # Get detailed plan from planner
            plan: Plan = await self._planner.create_user_edit_plan(edit)
            if plan:
                plan.section_title = edit["title"] \
                      if edit["type"] != "ADD" else None
                plan.section_path = edit["data"]["newPath"] \
                      if edit["type"] == "ADD" else None
                todo_items.append(plan)

        # Process items in batches
        await self._process_updates_in_batches(todo_items)

        # Save biography after all updates are complete
        await self._section_writer.save_biography()
    
    async def get_session_topics(self) -> List[str]:
        """To user: Get list of topics covered in this session"""
        return await self._session_summary_writer.extract_session_topics()

    async def set_selected_topics(self, topics: List[str]):
        """From user: Set the selected topics for session note update"""
        self._session_summary_writer.set_selected_topics(topics)
        
    def _collect_follow_up_questions(self) -> List[Dict]:
        """Collect follow-up questions from planner and section writer."""
        questions = []
        questions.extend(self._planner.follow_up_questions)
        questions.extend(self._section_writer.follow_up_questions)
        return questions
