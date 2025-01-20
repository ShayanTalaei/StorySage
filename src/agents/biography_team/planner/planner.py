import json
from typing import Dict, List, TYPE_CHECKING, Optional, Type
from pydantic import BaseModel, Field
from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException

from agents.biography_team.base_biography_agent import BiographyConfig, BiographyTeamAgent
from agents.biography_team.models import TodoItem
from agents.biography_team.planner.prompts import get_prompt
from biography.biography import Section
from biography.biography_styles import BIOGRAPHY_STYLE_PLANNER_INSTRUCTIONS

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
        self.follow_up_questions = []
        self.plans: List[TodoItem] = []
        
        # Initialize tools
        self.tools = {
            "add_plan": AddPlan(planner=self),
            "add_follow_up_question": AddFollowUpQuestion(planner=self)
        }
    
    def _get_full_biography_content(self) -> str:
        """
        Get the full content of the biography in a structured format.
        """
        def format_section(section: Section):
            content = []
            content.append(f"[{section.title}]")
            if section.content:
                content.append(section.content)
            for subsection in section.subsections.values():
                content.extend(format_section(subsection))
            return content

        sections = []
        for section in self.biography.root.subsections.values():
            sections.extend(format_section(section))
        return "\n".join(sections)

    async def create_adding_new_memory_plans(self, new_memories: List[Dict]) -> List[Dict]:
        """
        Create update plans for the biography based on new memories.
        """
        prompt = get_prompt("add_new_memory_planner").format(
            biography_structure=json.dumps(self.get_biography_structure(), indent=2),
            biography_content=self._get_full_biography_content(),
            new_information="\n".join([
                "<memory>\n"
                f"<title>{m['title']}</title>\n"
                f"<content>{m['text']}</content>\n"
                "</memory>\n"
                for m in new_memories
            ]),
            style_instructions=BIOGRAPHY_STYLE_PLANNER_INSTRUCTIONS.get(
                self.config.get("biography_style")
            ),
            tool_descriptions=self.get_tools_description()
        )
        self.add_event(sender=self.name, tag="prompt", content=prompt)
        response = self.call_engine(prompt)
        self.add_event(sender=self.name, tag="llm_response", content=response)

        self.handle_tool_calls(response)
        
        return self.plans

    async def create_user_edit_plan(self, edit: Dict) -> Dict:
        """Create a detailed plan for user-requested edits."""
        if edit["type"] == "ADD":
            prompt = get_prompt("user_add_planner").format(
                biography_structure=json.dumps(self.get_biography_structure(), indent=2),
                biography_content=self._get_full_biography_content(),
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
                biography_content=self._get_full_biography_content(),
                section_title=edit['title'],
                selected_text=edit['data']['comment']['text'],
                user_comment=edit['data']['comment']['comment'],
                style_instructions=BIOGRAPHY_STYLE_PLANNER_INSTRUCTIONS.get(
                    self.config.get("biography_style")
                ),
                tool_descriptions=self.get_tools_description(["add_plan"])
            )

        self.add_event(sender=self.name, tag="user_edit_prompt", content=prompt)
        response = self.call_engine(prompt)
        self.add_event(sender=self.name, tag="user_edit_response", content=response)

        # Handle tool calls to create plan
        self.handle_tool_calls(response)
        
        # Return just the latest plan
        return self.plans[-1] if self.plans else None

class AddPlanInput(BaseModel):
    action_type: str = Field(description="Type of action (create/update)")
    section_path: str = Field(description="Full path to the section")
    relevant_memories: Optional[str] = Field(
        default=None, 
        description="Optional: List of memories in bullet points format, e.g. '- Memory 1\n- Memory 2'"
    )
    update_plan: str = Field(description="Detailed plan for updating/creating the section")

class AddPlan(BaseTool):
    """Tool for adding a biography update plan."""
    name: str = "add_plan"
    description: str = "Add a plan for updating or creating a biography section"
    args_schema: Type[BaseModel] = AddPlanInput
    planner: BiographyPlanner = Field(...)

    def _run(
        self,
        action_type: str,
        section_path: str,
        update_plan: str,
        relevant_memories: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            self.planner.plans.append({
                "action_type": action_type,
                "section_path": section_path,
                "relevant_memories": relevant_memories.strip() if relevant_memories else None,
                "update_plan": update_plan
            })
            return f"Successfully added plan for {section_path}"
        except Exception as e:
            raise ToolException(f"Error adding plan: {str(e)}")

class AddFollowUpQuestionInput(BaseModel):
    content: str = Field(description="The question to ask")
    context: str = Field(description="Context explaining why this question is important")

class AddFollowUpQuestion(BaseTool):
    """Tool for adding follow-up questions."""
    name: str = "add_follow_up_question"
    description: str = (
        "Add a follow-up question that needs to be asked to gather more information for the biography. "
        "Include both the question and context explaining why this information is needed."
    )
    args_schema: Type[BaseModel] = AddFollowUpQuestionInput
    planner: BiographyPlanner = Field(...)

    def _run(
        self,
        content: str,
        context: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            self.planner.follow_up_questions.append({
                "content": content.strip(),
                "context": context.strip()
            })
            return f"Successfully added follow-up question: {content}"
        except Exception as e:
            raise ToolException(f"Error adding follow-up question: {str(e)}")