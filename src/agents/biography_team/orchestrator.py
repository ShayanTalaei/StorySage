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
            self._session_note_agent = SessionSummaryWriter(
                config, interview_session)
            self._interview_session = interview_session
        else:
            # Setup logging for non-interview operations
            setup_default_logger(
                user_id=config.get("user_id"),
                log_type="user_edits",
                log_level=logging.INFO
            )

        # Flag to track if biography update is in progress
        self.update_in_progress = False

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

    async def _plan_and_update_biography(self, new_memories: List[Memory]):
        """Handle the biography content updates (planner and section writer)"""
        # 1. Get plans from planner
        plans = await self._planner.create_adding_new_memory_plans(new_memories)
        SessionLogger.log_to_file("execution_log", 
                                  f"[BIOGRAPHY] Planned updates for biography")

        # 2. Execute section updates in parallel batches
        await self._process_updates_in_batches(plans)
        SessionLogger.log_to_file("execution_log", 
                                  f"[BIOGRAPHY] Executed updates for biography")
        
        # Save biography after all updates are complete
        await self._section_writer.save_biography(save_markdown=True)

    async def update_biography_and_notes(self, selected_topics: Optional[List[str]] = None):
        """Update biography with new memories."""
        try:
            self.update_in_progress = True

            # Get memories after note taker finishes
            new_memories: List[Memory] = await (
                self._interview_session.get_session_memories()
            )

            # 1. First process biography updates
            await self._plan_and_update_biography(new_memories)

            # 2. Collect follow-up questions after biography updates
            follow_up_questions = self._collect_follow_up_questions()

            # 3. Process session note update
            session_note_task = asyncio.create_task(
                self._session_note_agent.update_session_note(
                    new_memories=new_memories,
                    follow_up_questions=follow_up_questions
                )
            )

            # If topics are provided now, set them immediately
            if selected_topics is not None:
                self._session_note_agent.set_selected_topics(selected_topics)

            # Wait for session note task to complete
            await session_note_task

            # Save session note after all updates are complete
            self._interview_session.session_note.save(increment_session_id=True)

        finally:
            self.update_in_progress = False

    async def process_user_edits(self, edits: List[Dict]):
        """Process user-requested edits to the biography.
        This is used for the API mode and non-interview sessions."""
        todo_items: List[Plan] = []

        for edit in edits:
            # Get detailed plan from planner
            plan: Plan = await self._planner.create_user_edit_plan(edit)
            if plan:
                plan.section_title = edit["title"] if edit["type"] != "ADD" else None
                plan.section_path = edit["data"]["newPath"] if edit["type"] == "ADD" else None
                todo_items.append(plan)

        # Process items in batches
        await self._process_updates_in_batches(todo_items)

        # Save biography after all updates are complete
        await self._section_writer.save_biography()
    
    async def get_session_topics(self) -> List[str]:
        """To user: Get list of topics covered in this session"""
        return await self._session_note_agent.extract_session_topics()

    async def set_selected_topics(self, topics: List[str]):
        """From user: Set the selected topics for session note update"""
        self._session_note_agent.set_selected_topics(topics)
        
    def _collect_follow_up_questions(self) -> List[Dict]:
        """Collect follow-up questions from planner and section writer."""
        questions = []
        questions.extend(self._planner.follow_up_questions)
        questions.extend(self._section_writer.follow_up_questions)
        return questions
