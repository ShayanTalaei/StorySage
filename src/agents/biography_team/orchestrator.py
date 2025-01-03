from typing import Dict, List, TYPE_CHECKING
import asyncio
import os
from dotenv import load_dotenv

from agents.biography_team.base_biography_agent import BiographyConfig
from agents.biography_team.planner import BiographyPlanner
from agents.biography_team.section_writer import SectionWriter
from agents.biography_team.session_summary_writer import SessionSummaryWriter
from agents.biography_team.models import TodoItem

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession

load_dotenv()

class BiographyOrchestrator:
    def __init__(self, config: BiographyConfig, interview_session: 'InterviewSession'):
        self.config = config
        self.todo_items: List[TodoItem] = []
        self.planner = BiographyPlanner(config, interview_session)
        self.section_writer = SectionWriter(config, interview_session)
        self.session_note_agent = SessionSummaryWriter(config, interview_session)
        self.max_concurrent_updates = int(os.getenv("MAX_CONCURRENT_UPDATES", 5))
        
    async def update_biography(self, new_memories: List[Dict]):
        # 1. Get plans from planner
        plans = await self.planner.create_update_plans(new_memories)
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
        self.section_writer.save_biography()
        
        # 3. Update session notes
        follow_up_questions = self._collect_follow_up_questions()
        await self.session_note_agent.update_session_note(
            new_memories=new_memories,
            follow_up_questions=follow_up_questions
        )
    
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