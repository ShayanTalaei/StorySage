from typing import Dict, List, TYPE_CHECKING, Optional
import asyncio
import os
from dotenv import load_dotenv
import logging
import concurrent.futures

from agents.biography_team.base_biography_agent import BiographyConfig
from agents.biography_team.planner.planner import BiographyPlanner
from agents.biography_team.section_writer.section_writer import SectionWriter
from agents.biography_team.session_summary_writer.session_summary_writer import SessionSummaryWriter
from agents.biography_team.models import TodoItem
from utils.logger import setup_default_logger

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession

load_dotenv()


class BiographyOrchestrator:
    def __init__(self, config: BiographyConfig, interview_session: Optional['InterviewSession']):
        # Config and settings
        self.config = config
        self.max_concurrent_updates = int(
            os.getenv("MAX_CONCURRENT_UPDATES", 5))

        # Planning and writing agents
        self.todo_items: List[TodoItem] = []
        self.planner = BiographyPlanner(config, interview_session)
        self.section_writer = SectionWriter(config, interview_session)

        # Session note agent if it is an post-interview update
        if interview_session:
            self.session_note_agent = SessionSummaryWriter(
                config, interview_session)
            self.interview_session = interview_session
        else:
            # Setup logging for non-interview operations
            setup_default_logger(
                user_id=config.get("user_id"),
                log_type="user_edits",
                log_level=logging.INFO
            )

        # Flag to track if biography update is in progress
        self.update_in_progress = False

    async def _process_section_update(self, item: TodoItem) -> None:
        """Process a single section update."""
        try:
            result = await self.section_writer.update_section(item)
            item.status = "completed" if result.success else "failed"
        except Exception as e:
            item.status = "failed"
            item.error = str(e)

    def _collect_follow_up_questions(self) -> List[Dict]:
        """Collect follow-up questions from planner and section writer."""
        questions = []
        questions.extend(self.planner.follow_up_questions)
        questions.extend(self.section_writer.follow_up_questions)
        return questions

    async def get_session_topics(self) -> List[str]:
        """To user: Get list of topics covered in this session"""
        return await self.session_note_agent.extract_session_topics()

    async def set_selected_topics(self, topics: List[str]):
        """From user: Set the selected topics for session note update"""
        self.session_note_agent.set_selected_topics(topics)

    async def _process_updates_in_batches(self, items: List[TodoItem]) -> None:
        """Process todo items using thread pool for parallel execution."""
        pending_items = [item for item in items if item.status == "pending"]

        # Process in batches to control concurrency
        for i in range(0, len(pending_items), self.max_concurrent_updates):
            batch = pending_items[i:i + self.max_concurrent_updates]

            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = []
                for item in batch:
                    item.status = "in_progress"
                    # Wrap async function for thread execution
                    future = executor.submit(
                        lambda i=item: asyncio.run(
                            self._process_section_update(i))
                    )
                    futures.append(future)

                # Wait for batch completion
                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result()  # Get result to propagate exceptions
                    except Exception as e:
                        print(f"Error processing item: {str(e)}")

    async def _update_biography_content(self, new_memories: List[Dict]):
        """Handle the biography content updates (planner and section writer)"""
        # 1. Get plans from planner
        plans = await self.planner.create_adding_new_memory_plans(new_memories)
        self.todo_items.extend([TodoItem(**plan) for plan in plans])

        # 2. Execute section updates in parallel batches
        await self._process_updates_in_batches(self.todo_items)

        # Save biography after all updates are complete
        self.section_writer.save_biography(save_markdown=True)

    async def update_biography(self, selected_topics: Optional[List[str]] = None):
        """Update biography with new memories."""
        try:
            self.update_in_progress = True

            # Get memories after note taker finishes
            new_memories = await self.interview_session.get_session_memories()

            # 1. First process biography updates
            await self._update_biography_content(new_memories)

            # 2. Collect follow-up questions after biography updates
            follow_up_questions = self._collect_follow_up_questions()

            # 3. Process session note update
            session_note_task = asyncio.create_task(
                self.session_note_agent.update_session_note(
                    new_memories=new_memories,
                    follow_up_questions=follow_up_questions
                )
            )

            # If topics are provided now, set them immediately
            if selected_topics is not None:
                self.session_note_agent.set_selected_topics(selected_topics)

            # Wait for session note task to complete
            await session_note_task

            # Save session note after all updates are complete
            self.interview_session.session_note.increment_session_id()
            self.interview_session.session_note.save()

        finally:
            self.update_in_progress = False

    async def process_user_edits(self, edits: List[Dict]):
        """Process user-requested edits to the biography.
        This is used for the API mode and non-interview sessions."""
        todo_items: List[TodoItem] = []

        for edit in edits:
            # Get detailed plan from planner
            plan = await self.planner.create_user_edit_plan(edit)
            if plan:
                plan["section_title"] = edit["title"] if edit["type"] != "ADD" else None
                plan["section_path"] = edit["data"]["newPath"] if edit["type"] == "ADD" else None
                todo_items.append(TodoItem(**plan))

        # Process items in batches
        await self._process_updates_in_batches(todo_items)

        # Save biography after all updates are complete
        self.section_writer.save_biography()
