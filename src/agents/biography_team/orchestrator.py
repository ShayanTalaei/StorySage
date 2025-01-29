from typing import Dict, List, TYPE_CHECKING, Optional
import asyncio
import os
from dotenv import load_dotenv
import logging

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
        self.config = config
        self.todo_items: List[TodoItem] = []
        self.planner = BiographyPlanner(config, interview_session)
        self.section_writer = SectionWriter(config, interview_session)
        if interview_session:
            self.session_note_agent = SessionSummaryWriter(config, interview_session)
        else:
            # Setup logging for non-session operations
            setup_default_logger(
                user_id=config.get("user_id"),
                log_type="user_edits",
                log_level=logging.INFO
            )
        self.max_concurrent_updates = int(os.getenv("MAX_CONCURRENT_UPDATES", 5))
    
    async def _process_section_update(self, item: TodoItem) -> None:
        """Process a single section update."""
        try:
            result = await self.section_writer.update_section(item)
            item.status = "completed" if result.success else "failed"
        except Exception as e:
            item.status = "failed"
            item.error = str(e)
        
    def _collect_follow_up_questions(self) -> List[Dict]:
        questions = []
        questions.extend(self.planner.follow_up_questions)
        questions.extend(self.section_writer.follow_up_questions)
        return questions 
        
    async def update_biography(self, new_memories: List[Dict]):
        # 1. Get plans from planner
        plans = await self.planner.create_adding_new_memory_plans(new_memories)
        self.todo_items.extend([TodoItem(**plan) for plan in plans])
        
        # 2. Execute section updates in parallel
        pending_items = [item for item in self.todo_items if item.status == "pending"]
        
        # Process items in batches to control concurrency
        for i in range(0, len(pending_items), self.max_concurrent_updates):
            batch = pending_items[i:i + self.max_concurrent_updates]
            update_tasks = []
            
            for item in batch:
                item.status = "in_progress"
                task = self._process_section_update(item)
                update_tasks.append(task)
            
            # Wait for all tasks in this batch to complete
            await asyncio.gather(*update_tasks)
        
        # Save biography after all updates are complete
        self.section_writer.save_biography(save_markdown=True)
        
        # 3. Update session notes
        follow_up_questions = self._collect_follow_up_questions()
        await self.session_note_agent.update_session_note(
            new_memories=new_memories,
            follow_up_questions=follow_up_questions
        )
    
    async def process_user_edits(self, edits: List[Dict]):
        """Process user-requested edits to the biography."""
        todo_items: List[TodoItem] = []
        
        for edit in edits:
            # Get detailed plan from planner
            plan = await self.planner.create_user_edit_plan(edit)
            if plan:
                plan["section_title"] = edit["title"] if edit["type"] != "ADD" else None
                plan["section_path"] = edit["data"]["newPath"] if edit["type"] == "ADD" else None
                todo_items.append(TodoItem(**plan))
        
        # Process items in batches to control concurrency
        pending_items = [item for item in todo_items if item.status == "pending"]
        
        for i in range(0, len(pending_items), self.max_concurrent_updates):
            batch = pending_items[i:i + self.max_concurrent_updates]
            update_tasks = []
            
            for item in batch:
                item.status = "in_progress"
                task = self._process_section_update(item)
                update_tasks.append(task)
            
            # Wait for all tasks in this batch to complete
            await asyncio.gather(*update_tasks)
        
        # Save biography after all updates are complete
        self.section_writer.save_biography() 