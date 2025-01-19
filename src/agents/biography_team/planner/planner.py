from typing import Dict, List, TYPE_CHECKING, Optional
from agents.biography_team.base_biography_agent import BiographyConfig, BiographyTeamAgent
import json
import xml.etree.ElementTree as ET
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

    async def create_update_plans(self, new_memories: List[Dict]) -> List[Dict]:
        """
        Create update plans for the biography based on new memories.
        """
        prompt = self._create_planning_prompt(new_memories)
        self.add_event(sender=self.name, tag="prompt", content=prompt)
        response = self.call_engine(prompt)
        self.add_event(sender=self.name, tag="llm_response", content=response)

        plans = self._parse_plans(response)
        
        self.follow_up_questions = self._parse_questions(response)

        return plans

    def _create_planning_prompt(self, new_memories: List[Dict]) -> str:
        """
        Create a prompt for the planner to analyze new memories and create update plans.
        """        
        # # Get all relevant memories from memory bank
        # relevant_memories_dict = {}
        # for memory in new_memories:
        #     search_results = self.memory_bank.search_memories(memory['text'], k=3)
        #     for result in search_results:
        #         relevant_memories_dict[result['id']] = result
        # relevant_memories = list(relevant_memories_dict.values())
        # self.add_event(sender=self.name, tag="memory_search_complete", 
        #                content=f"{relevant_memories}")
        
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
            )
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

    def _parse_plans(self, response: str) -> List[Dict]:
        """
        Parse the response to extract update plans and follow-up questions.
        """
        plans = []
        try:
            if "<plans>" in response:
                start_tag = "<plans>"
                end_tag = "</plans>"
                start_pos = response.find(start_tag)
                end_pos = response.find(end_tag) + len(end_tag)
                plans_text = response[start_pos:end_pos]
                root = ET.fromstring(plans_text)
                for plan in root.findall("plan"):
                    action_type = plan.find("action_type").text.strip()
                    section_path = plan.find("section_path").text.strip()
                    
                    plans.append({
                        "action_type": action_type,
                        "section_path": section_path,
                        "relevant_memories": self._parse_relevant_memories(plan),
                        "update_plan": plan.find("update_plan").text.strip()
                    })
        except Exception as e:
            self.add_event(sender=self.name, tag="error", 
                          content=f"Error parsing plans: {str(e)}\nResponse: {response}")
            raise e
        return plans

    def _parse_questions(self, response: str) -> List[Dict]:
        """
        Parse the response to extract follow-up questions.
        """
        questions = []
        try:
            if "<follow_up_questions>" in response:
                start_tag = "<follow_up_questions>"
                end_tag = "</follow_up_questions>"
                start_pos = response.find(start_tag)
                end_pos = response.find(end_tag) + len(end_tag)
                questions_text = response[start_pos:end_pos]
                root = ET.fromstring(questions_text)
                for question in root.findall("question"):
                    content_elem = question.find("content")
                    context_elem = question.find("context")
                    if content_elem is not None and content_elem.text:
                        questions.append({
                            "content": content_elem.text.strip(),
                            "context": context_elem.text.strip() if context_elem is not None else ""
                        })
        except Exception as e:
            self.add_event(sender=self.name, tag="error", 
                          content=f"Error parsing questions: {str(e)}\nResponse: {response}")
            raise e
        return questions

    def _parse_relevant_memories(self, plan: ET.Element) -> List[str]:
        """
        Parse the relevant memories from a plan element.
        """
        memories = []
        try:
            memories_elem = plan.find("relevant_memories")
            if memories_elem is not None:
                for memory in memories_elem.findall("memory"):
                    memories.append(memory.text.strip())
        except Exception as e:
            self.add_event(sender=self.name, tag="error", 
                          content=f"Error parsing relevant memories: {str(e)}")
            raise e
        return memories
