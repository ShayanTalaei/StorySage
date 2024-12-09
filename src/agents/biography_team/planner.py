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
        prompt = self._create_planning_prompt(new_memories)
        response = self.call_engine(prompt)

        # Parse response to get plans and follow-up questions
        plans = self._parse_plans(response)
        self.follow_up_questions = self._parse_questions(response)

        return plans

    def _create_planning_prompt(self, new_memories: List[Dict]) -> str:
        # Get all relevant memories from memory bank
        relevant_memories_dict = {}  # Use memory ID as key
        for memory in new_memories:
            search_results = self.memory_bank.search_memories(
                memory['text'], k=3)
            for result in search_results:
                relevant_memories_dict[result['id']] = result
        
        relevant_memories = list(relevant_memories_dict.values())

        return PLANNER_SYSTEM_PROMPT.format(
            biography_structure=json.dumps(
                self.get_biography_structure(), indent=2),
            biography_content=self._get_full_biography_content(),
            new_information="\n".join([f"- {m['text']}" for m in new_memories]),
            relevant_information="\n".join(
                [f"- {m['text']} (Similarity: {m['similarity_score']:.2f})" for m in relevant_memories])
        )

    def _get_full_biography_content(self) -> str:
        """Get the full content of the biography in a structured format."""
        def format_section(section, indent=0):
            content = []
            content.append("  " * indent + f"[{section.title}]")
            if section.content:
                content.append("  " * (indent + 1) + section.content)
            for subsection in section.subsections.values():
                content.extend(format_section(subsection, indent + 1))
            return content

        sections = []
        for section in self.biography.root.subsections.values():
            sections.extend(format_section(section))
        return "\n".join(sections)

    def _parse_plans(self, response: str) -> List[Dict]:
        plans = []
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
                
                if action_type == "create":
                    plans.append({
                        "action_type": "create",
                        "section_path": section_path,
                        "section_title": plan.find("section_title").text.strip(),
                        "update_plan": plan.find("update_plan").text.strip()
                    })
                else:  # update
                    plans.append({
                        "action_type": "update",
                        "section_path": section_path,
                        "update_plan": plan.find("update_plan").text.strip()
                    })
        return plans

    def _parse_questions(self, response: str) -> List[Dict]:
        questions = []
        if "<follow_up_questions>" in response:
            start_tag = "<follow_up_questions>"
            end_tag = "</follow_up_questions>"
            start_pos = response.find(start_tag)
            end_pos = response.find(end_tag) + len(end_tag)
            questions_text = response[start_pos:end_pos]
            root = ET.fromstring(questions_text)
            for question in root.findall("question"):
                questions.append({
                    "question": question.text.strip(),
                    "type": "breadth"
                })
        return questions

# TODO-lmj: we should handle invalid paths in biography.py because the LLM may not follow the rules in the prompt sometimes.
PLANNER_SYSTEM_PROMPT = """
You are a biography expert. We are interviewing a user and collecting new information about them to write their biography.
Your task is to analyze new information and plan updates to the biography.

Current Biography Structure:
<biography_structure>
{biography_structure}
</biography_structure>

Current Biography Content:
<biography_content>
{biography_content}
</biography_content>

New Information to Add:
<new_information>
{new_information}
</new_information>

Related Previous Information:
<relevant_information>
{relevant_information}
</relevant_information>

Your task is to:
1. Analyze the new information and their relationship with existing content
2. Determine whether to:
   a. Update existing sections or subsections
   b. Create new sections or subsections
3. Create specific plans for each action
4. Suggest follow-up questions to expand the biography's breadth

For each plan, consider:
- How the new information connects to existing content
- Whether it reinforces existing themes or introduces new ones
- Where the information best fits in the biography's structure
- How to maintain narrative flow and coherence
- Whether the information warrants a new section or subsection

Provide your response in the following XML format:

<plans>
    <!-- For creating new sections -->
    <plan>
        <action_type>create</action_type>
        <section_path>Parent section path (e.g., "1 Early Life/1.1 Childhood")</section_path>
        <section_title>Title of the new section</section_title>
        <update_plan>Detailed description of the new section content, including:
        - What information to include
        - How to structure the content
        - Key points to emphasize</update_plan>
    </plan>

    <!-- For updating existing sections -->
    <plan>
        <action_type>update</action_type>
        <section_path>Full path to existing section</section_path>
        <update_plan>Detailed description of how to update the section, including:
        - What new information to add
        - How to integrate it with existing content
        - Any restructuring needed
        - Key points to emphasize</update_plan>
    </plan>
</plans>

<follow_up_questions>
    <question>Question text that would help expand the biography's breadth</question>
    ...
</follow_up_questions>

Important Notes about the XML format:
- Use action_type="create" when adding a new section
- Use action_type="update" when modifying an existing section
- For "create" actions, both section_path and section_title are required
- For "update" actions, only section_path is needed
- Each plan must include a detailed update_plan explaining the changes

Important Note About Section Paths:
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
    
Examples of valid paths:
  * "1 Early Life"
  * "2 Career/2.1 Software Projects/First App"
  * "3 Personal Life/3.2 Hobbies/Gaming/Favorite Games"

Invalid paths:
  * "Early Life" (missing first level number)
  * "1 Early Life/Childhood" (missing second level number)
  * "1.1 Childhood" (subsection without parent section)
  * "1 Early Life/1.1 Childhood/Games/Types/Specific" (exceeds 4 levels)
"""
