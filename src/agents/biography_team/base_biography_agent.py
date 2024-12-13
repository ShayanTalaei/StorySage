from typing import Dict, TYPE_CHECKING
from agents.base_agent import BaseAgent
from interview_session.session_models import Participant
from memory_bank.memory_bank_vector_db import MemoryBank
from biography.biography import Biography

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession

class BiographyTeamAgent(BaseAgent, Participant):
    def __init__(self, name: str, description: str, config: Dict, interview_session: 'InterviewSession'):
        BaseAgent.__init__(self, name=name, description=description, config=config)
        Participant.__init__(self, title=name, interview_session=interview_session)
        user_id = config.get("user_id")
        # TODO-lmj: we should not maintain the memory bank and biography object in the base agent.
        self.memory_bank = MemoryBank.load_from_file(user_id)
        self.biography = Biography.load_from_file(user_id)
        
    def get_biography_structure(self):
        return self.biography.get_sections() 