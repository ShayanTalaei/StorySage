from typing import Dict, List, TYPE_CHECKING

from agents.biography_team.planner import BiographyPlanner
from agents.biography_team.section_writer import SectionWriter
from agents.biography_team.session_note_agent import SessionNoteAgent
from agents.biography_team.models import TodoItem

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession

class BiographyOrchestrator:
    def __init__(self, config: Dict, interview_session: 'InterviewSession'):
        self.config = config
        self.todo_items: List[TodoItem] = []
        self.planner = BiographyPlanner(config, interview_session)
        self.section_writer = SectionWriter(config, interview_session)
        self.session_note_agent = SessionNoteAgent(config, interview_session)
        
    async def update_biography(self, new_memories: List[Dict]):
        # 1. Get plans from planner
        plans = await self.planner.create_update_plans(new_memories)
        self.todo_items.extend([TodoItem(**plan) for plan in plans])
        
        # 2. Execute section updates
        for item in self.todo_items:
            if item.status == "pending":
                item.status = "in_progress"
                
                result = await self.section_writer.update_section(item)
                if result.success:
                    item.status = "completed"
                else:
                    item.status = "failed"        
        self.section_writer.save_biography()
        
        # 3. Update session notes
        follow_up_questions = self._collect_follow_up_questions()
        await self.session_note_agent.update_session_note(
            new_memories=new_memories,
            follow_up_questions=follow_up_questions
        )
        
    def _collect_follow_up_questions(self) -> List[Dict]:
        questions = []
        questions.extend(self.planner.follow_up_questions)
        questions.extend(self.section_writer.follow_up_questions)
        return questions 