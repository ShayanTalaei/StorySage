import json
import os
from typing import Dict, List, TYPE_CHECKING, Optional

from agents.biography_team.base_biography_agent import BiographyConfig, BiographyTeamAgent
from agents.biography_team.models import Plan, FollowUpQuestion
from agents.biography_team.planner.prompts import get_prompt
from agents.biography_team.planner.tools import AddPlan
from agents.shared.note_tools import AddFollowUpQuestion
from content.biography.biography_styles import BIOGRAPHY_STYLE_PLANNER_INSTRUCTIONS
from content.memory_bank.memory import Memory
from utils.llm.xml_formatter import extract_tool_arguments

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
        
        self.tools = {
            "add_plan": AddPlan(
                on_plan_added=lambda p: self.plans.append(p)
            ),
            "add_follow_up_question": AddFollowUpQuestion(
                on_question_added=lambda q: self.follow_up_questions.append(q)
            )
        }

    async def create_adding_new_memory_plans(self, new_memories: List[Memory]) -> List[Plan]:
        """Create update plans for the biography based on new memories."""
        max_iterations = int(os.getenv("MAX_CONSIDERATION_ITERATIONS", "3"))
        iterations = 0
        all_memory_ids = set(memory.id for memory in new_memories)
        covered_memory_ids = set()
        previous_tool_call = None
        
        while iterations < max_iterations:
            prompt = self._get_formatted_prompt(
                "add_new_memory_planner",
                new_memories=new_memories,
                previous_tool_call=previous_tool_call,
                missing_memory_ids="\n".join(
                    sorted(list(all_memory_ids - covered_memory_ids))
                ) if previous_tool_call else ""
            )
            
            self.add_event(
                sender=self.name,
                tag="add_new_memory_prompt", 
                content=prompt
            )
            
            response = await self.call_engine_async(prompt)
            self.add_event(
                sender=self.name,
                tag="add_new_memory_response",
                content=response
            )

            # Check if agent wants to proceed with missing memories
            if "<proceed>true</proceed>" in response.lower():
                self.add_event(
                    sender=self.name,
                    tag="feedback_loop",
                    content="Agent chose to proceed with missing memories"
                )
                break

            # Extract tool calls section
            tool_calls_start = response.find("<tool_calls>")
            tool_calls_end = response.find("</tool_calls>")
            if tool_calls_start != -1 and tool_calls_end != -1:
                tool_calls_xml = response[
                    tool_calls_start:tool_calls_end + len("</tool_calls>")
                ]
                
                # Extract memory IDs from add_plan tool calls
                memory_ids = extract_tool_arguments(
                    tool_calls_xml, "add_plan", "memory_ids"
                )
                current_memory_ids = set()
                for ids in memory_ids:
                    if isinstance(ids, (list, set)):
                        current_memory_ids.update(ids)
                    else:
                        current_memory_ids.add(ids)
                
                # Update covered memories
                covered_memory_ids.update(current_memory_ids)
                
                # Save tool calls for next iteration if needed
                previous_tool_call = tool_calls_xml
            
            # Check if all memories are covered
            if covered_memory_ids >= all_memory_ids:
                self.add_event(
                    sender=self.name,
                    tag="feedback_loop",
                    content="All memories covered in plans"
                )
                break
            
            iterations += 1
            
            if iterations == max_iterations:
                self.add_event(
                    sender=self.name,
                    tag="warning",
                    content=f"Reached max iterations ({max_iterations}) "
                            "without covering all memories"
                )

        # Handle the final tool calls
        self.handle_tool_calls(response)
        
        return self.plans

    async def create_user_edit_plan(self, edit: Dict) -> Plan:
        """Create a detailed plan for user-requested edits."""
        if edit["type"] == "ADD":   # ADD
            prompt = self._get_formatted_prompt(
                "user_add_planner",
                section_path=edit['data']['newPath'],
                section_prompt=edit['data']['sectionPrompt']
            )
        else:  # COMMENT
            prompt = self._get_formatted_prompt(
                "user_comment_planner",
                section_title=edit['title'],
                selected_text=edit['data']['comment']['text'],
                user_comment=edit['data']['comment']['comment']
            )

        self.add_event(sender=self.name, tag="user_edit_prompt", content=prompt)
        response = await self.call_engine_async(prompt)
        self.add_event(sender=self.name, tag="user_edit_response", content=response)

        # Handle tool calls to create plan
        self.handle_tool_calls(response)
        
        # Return just the latest plan
        return self.plans[-1] if self.plans else None

    def _get_formatted_prompt(self, prompt_type: str, **kwargs) -> str:
        """
        Format prompt with the appropriate parameters based on prompt type.
        
        Args:
            prompt_type: Type of prompt to format
            **kwargs: Additional parameters specific to the prompt type
        """
        base_params = {
            "biography_structure": json.dumps(self.get_biography_structure(), indent=2),
            "biography_content": self.biography.export_to_markdown(),
            "style_instructions": BIOGRAPHY_STYLE_PLANNER_INSTRUCTIONS.get(
                self.config.get("biography_style")
            )
        }

        prompt_params = {
            "add_new_memory_planner": {
                **base_params,
                "new_information": '\n\n'.join(
                    [memory.to_xml() for memory in kwargs.get('new_memories', [])]
                ),
                "tool_descriptions": self.get_tools_description(
                    ["add_plan", "add_follow_up_question"]),
                "previous_tool_call": kwargs.get('previous_tool_call', ""),
                "missing_memory_ids": kwargs.get('missing_memory_ids', "")
            },
            "user_add_planner": {
                **base_params,
                "section_path": kwargs.get('section_path'),
                "section_prompt": kwargs.get('section_prompt'),
                "tool_descriptions": self.get_tools_description(["add_plan"])
            },
            "user_comment_planner": {
                **base_params,
                "section_title": kwargs.get('section_title'),
                "selected_text": kwargs.get('selected_text'),
                "user_comment": kwargs.get('user_comment'),
                "tool_descriptions": self.get_tools_description(["add_plan"])
            }
        }

        return get_prompt(
            prompt_type,
            include_warning=(kwargs.get('previous_tool_call') is not None)
        ).format(**prompt_params[prompt_type])