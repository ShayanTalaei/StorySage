import json
from typing import Dict, List, TYPE_CHECKING, Optional, Type
from pydantic import BaseModel, Field
from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException

from agents.biography_team.base_biography_agent import BiographyConfig, BiographyTeamAgent
from agents.biography_team.models import TodoItem
from agents.biography_team.planner.prompts import PLANNER_SYSTEM_PROMPT
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

    async def create_update_plans(self, new_memories: List[Dict]) -> List[Dict]:
        """
        Create update plans for the biography based on new memories.
        """
        prompt = self._create_planning_prompt(new_memories)
        self.add_event(sender=self.name, tag="prompt", content=prompt)
        response = self.call_engine(prompt)
        self.add_event(sender=self.name, tag="llm_response", content=response)

        # Handle tool calls to create plans and questions
        self.handle_tool_calls(response)
        
        return self.plans

    def _create_planning_prompt(self, new_memories: List[Dict]) -> str:
        """
        Create a prompt for the planner to analyze new memories and create update plans.
        """        
        
        prompt = PLANNER_SYSTEM_PROMPT.format(
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
        
        return prompt

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

class AddPlanInput(BaseModel):
    action_type: str = Field(description="Type of action (create/update)")
    section_path: str = Field(description="Full path to the section")
    relevant_memories: str = Field(description="List of memories in bullet points format, e.g. '- Memory 1\n- Memory 2'")
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
        relevant_memories: str,
        update_plan: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            self.planner.plans.append({
                "action_type": action_type,
                "section_path": section_path,
                "relevant_memories": relevant_memories.strip(),
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