import json
from typing import Dict, List, TYPE_CHECKING, Optional

from agents.biography_team.base_biography_agent import BiographyConfig, BiographyTeamAgent
from agents.biography_team.shared.models import Plan, FollowUpQuestion
from agents.biography_team.planner.prompts import get_prompt
from agents.biography_team.planner.tools import AddPlan
from agents.biography_team.shared.tools import AddFollowUpQuestion
from content.biography.biography_styles import BIOGRAPHY_STYLE_PLANNER_INSTRUCTIONS
from content.memory_bank.memory import Memory

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession


class BiographyPlanner(BiographyTeamAgent):
    def __init__(self, config: BiographyConfig, interview_session: Optional['InterviewSession'] = None):
        super().__init__(
            name="BiographyPlanner",
            description="Plans updates to the biography based on new memories",
            config=config,
            interview_session=interview_session
        )
        self.follow_up_questions: List[FollowUpQuestion] = []
        self.plans: List[Plan] = []
        
        # Initialize tools
        self.tools = {
            "add_plan": AddPlan(
                on_plan_added=lambda p: self.plans.append(p)
            ),
            "add_follow_up_question": AddFollowUpQuestion(
                on_question_added=lambda q: self.follow_up_questions.append(q)
            )
        }
    
    async def create_adding_new_memory_plans(self, new_memories: List[Memory]) -> List[Plan]:
        """
        Create update plans for the biography based on new memories.
        """
        prompt = get_prompt("add_new_memory_planner").format(
            biography_structure=json.dumps(self.get_biography_structure(), indent=2),
            biography_content=self.biography.export_to_markdown(),
            new_information='\n\n'.join(
                [memory.to_xml() for memory in new_memories]),
            style_instructions=BIOGRAPHY_STYLE_PLANNER_INSTRUCTIONS.get(
                self.config.get("biography_style")
            ),
            tool_descriptions=self.get_tools_description()
        )
        self.add_event(sender=self.name, tag="add_new_memory_prompt", content=prompt)
        response = await self.call_engine_async(prompt)
        self.add_event(sender=self.name, tag="add_new_memory_response", content=response)

        self.handle_tool_calls(response)
        
        return self.plans

    async def create_user_edit_plan(self, edit: Dict) -> Plan:
        """Create a detailed plan for user-requested edits."""
        if edit["type"] == "ADD":
            prompt = get_prompt("user_add_planner").format(
                biography_structure=json.dumps(self.get_biography_structure(), indent=2),
                biography_content=self.biography.export_to_markdown(),
                section_path=edit['data']['newPath'],
                section_prompt=edit['data']['sectionPrompt'],
                style_instructions=BIOGRAPHY_STYLE_PLANNER_INSTRUCTIONS.get(
                    self.config.get("biography_style")
                ),
                tool_descriptions=self.get_tools_description(["add_plan"])
            )
        else:  # COMMENT
            prompt = get_prompt("user_comment_planner").format(
                biography_structure=json.dumps(self.get_biography_structure(), indent=2),
                biography_content=self.biography.export_to_markdown(),
                section_title=edit['title'],
                selected_text=edit['data']['comment']['text'],
                user_comment=edit['data']['comment']['comment'],
                style_instructions=BIOGRAPHY_STYLE_PLANNER_INSTRUCTIONS.get(
                    self.config.get("biography_style")
                ),
                tool_descriptions=self.get_tools_description(["add_plan"])
            )

        self.add_event(sender=self.name, tag="user_edit_prompt", content=prompt)
        response = await self.call_engine_async(prompt)
        self.add_event(sender=self.name, tag="user_edit_response", content=response)

        # Handle tool calls to create plan
        self.handle_tool_calls(response)
        
        # Return just the latest plan
        return self.plans[-1] if self.plans else None
