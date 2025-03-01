from typing import Dict, TYPE_CHECKING, Optional, TypedDict, ClassVar
from agents.base_agent import BaseAgent
from interview_session.session_models import Participant
from content.biography.biography import Biography

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession

class BiographyConfig(TypedDict, total=False):
    """Configuration for the BiographyOrchestrator."""
    user_id: str
    biography_style: str  # e.g. 'narrative', 'chronological', etc.

class BiographyTeamAgent(BaseAgent, Participant):
    # Dictionary to store shared biographies by user_id
    _shared_biographies: ClassVar[Dict[str, Biography]] = {}
    
    def __init__(
        self,
        name: str,
        description: str,
        config: BiographyConfig,
        interview_session: Optional['InterviewSession'] = None
    ):
        # Initialize BaseAgent
        BaseAgent.__init__(self, name=name, description=description, config=config)
        
        # Initialize Participant if we have an interview session
        if interview_session:
            Participant.__init__(self, title=name,
                                 interview_session=interview_session)
        
        self.interview_session = interview_session
        
        # Get user_id from config
        user_id = config.get("user_id")
        
        # Use shared biography instance if it exists, otherwise create and store it
        if user_id not in BiographyTeamAgent._shared_biographies:
            BiographyTeamAgent._shared_biographies[user_id] = \
                Biography.load_from_file(user_id)
        
        # Use the shared biography instance
        self.biography = BiographyTeamAgent._shared_biographies[user_id]
        
    def get_biography_structure(self):
        return self.biography.get_sections() 