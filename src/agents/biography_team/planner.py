from typing import Dict, List, TYPE_CHECKING
from agents.biography_team.base_biography_agent import BiographyTeamAgent
import json
import xml.etree.ElementTree as ET

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession


class BiographyPlanner(BiographyTeamAgent):
    def __init__(self, config: Dict, interview_session: 'InterviewSession'):
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
            ])
        )
        
        return prompt

    def _get_full_biography_content(self) -> str:
        """
        Get the full content of the biography in a structured format.
        """
        def format_section(section):
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

PLANNER_SYSTEM_PROMPT = """
You are a biography expert. We are interviewing a user and collecting new information about the user to write his or her biography. Your task is to analyze new information and plan updates to the biography.

Input Context:
<biography_structure>
{biography_structure}
</biography_structure>

<biography_content>
{biography_content}
</biography_content>

<new_information>
{new_information}
</new_information>

Core Responsibilities:
- Analyze the new information and their relationship with existing content
- Determine whether to:
   * Update existing sections or subsections
   * Create new sections or subsections
- Create specific plans for each action
- Suggest follow-up questions to expand the biography's breadth

Guidance for Creating Plans:
- How the new information connects to existing content
- Whether it reinforces existing themes or introduces new ones
- Where the information best fits in the biography's structure
- How to maintain narrative flow and coherence
- Whether the information warrants a new section or subsection

Provide your response in the following XML format:

<plans>
    <plan>
        <action_type>create/update</action_type>
        <section_path>Full path to the section (e.g., "1 Early Life/1.1 Childhood/Memorable Events")</section_path>
        <relevant_memories>
            <!-- Each memory must be an exact copy from the <new_information> section -->
            <memory>The exact text copied from new_information</memory>
            <memory>Another exact text copied from new_information</memory>
        </relevant_memories>
        <update_plan>Detailed description of how to update/create the section, including:
        - How to integrate the specific memories copied above
        - How to structure or merge with existing content
        - Any restructuring needed
        - Key points to emphasize</update_plan>
    </plan>
</plans>

<follow_up_questions>
    <question>
        <context>
            One brief sentence explaining which memory/information this follows up on.
            Example: "Follows up on mother's garden memory to explore career influence."
        </context>
        <content>Question text that would help expand the biography's breadth</content>
    </question>
    ...
</follow_up_questions>

Important Notes about the XML Format:
<format_notes>
- Set action_type as "create" when adding a new section
- Set action_type as "update" when modifying an existing section
- The section_path is the full path to the section
- Each plan must include a detailed update_plan explaining the changes
</format_notes>

Important Note About Section Paths:
<format_notes>
- Section paths must be specified using forward slashes to indicate hierarchy
- Each part of the path should be the exact title of a section
- Maximum 4 levels of hierarchy allowed
- Numbering conventions:
  * First level sections must start with numbers: "1", "2", "3", etc.
    Examples: "1 Early Life", "2 Education", "3 Career"
  * Second level sections (subsections) use decimal notation matching parent number
    Examples: "1 Early Life/1.1 Childhood", "1 Early Life/1.2 Family Background"
  * Third and fourth levels do not use numbers
    Examples: "1 Early Life/1.1 Childhood/Memorable Events"
- Examples of valid paths:
  * "1 Early Life"
  * "2 Career/2.1 Software Projects/First App"
  * "3 Personal Life/3.2 Hobbies/Gaming/Favorite Games"
- Examples of invalid paths:
  * "Early Life" (missing first level number)
  * "1 Early Life/Childhood" (missing second level number)
  * "1.1 Childhood" (subsection without parent section)
  * "1 Early Life/1.1 Childhood/Games/Types/Specific" (exceeds 4 levels)
</format_notes>
"""