import json
from typing import Dict, List, TYPE_CHECKING, Optional

from agents.biography_team.base_biography_agent import BiographyConfig, BiographyTeamAgent
from agents.biography_team.models import Plan, FollowUpQuestion
from agents.biography_team.planner.prompts import get_prompt
from agents.biography_team.planner.tools import AddPlan
from agents.shared.feedback_prompts import MISSING_MEMORIES_WARNING
from agents.shared.note_tools import ProposeFollowUp
from content.biography.biography_styles import BIOGRAPHY_STYLE_PLANNER_INSTRUCTIONS
from content.memory_bank.memory import Memory
from utils.llm.xml_formatter import extract_tool_arguments, extract_tool_calls_xml

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
                on_plan_added=self._handle_plan_added
            ),
            "propose_follow_up": ProposeFollowUp(
                on_question_added=lambda q: self.follow_up_questions.append(q)
            )
        }

    async def create_adding_new_memory_plans(self, new_memories: List[Memory]) -> List[Plan]:
        """Create update plans for the biography based on new memories."""
        iterations = 0
        all_memory_ids = set(memory.id for memory in new_memories)
        covered_memory_ids = set()
        previous_tool_call = None
        
        # Clear any existing plans before starting
        self.plans = []
        
        while iterations < self._max_consideration_iterations:
            prompt = await self._get_formatted_prompt(
                "add_new_memory_planner",
                new_memories=new_memories,
                previous_tool_call=previous_tool_call,
                missing_memory_ids="\n".join(
                    sorted(list(all_memory_ids - covered_memory_ids))
                ) if previous_tool_call else ""
            )
            
            self.add_event(
                sender=self.name,
                tag=f"add_new_memory_prompt_{iterations}", 
                content=prompt
            )
            
            response = await self.call_engine_async(prompt)
            self.add_event(
                sender=self.name,
                tag=f"add_new_memory_response_{iterations}",
                content=response
            )

            # Handle tool calls for this iteration immediately
            self.handle_tool_calls(response)

            # Check if agent wants to proceed with missing memories
            if "<proceed>true</proceed>" in response.lower():
                self.add_event(
                    sender=self.name,
                    tag=f"feedback_loop_{iterations}",
                    content="Agent chose to proceed with missing memories"
                )
                break
                
            # Extract memory IDs from add_plan tool calls
            memory_ids = extract_tool_arguments(
                response, "add_plan", "memory_ids"
            )

            # Process memory IDs and add to current set
            current_memory_ids = set()
            for ids in memory_ids:
                if isinstance(ids, (list, set)):
                    # If it's already a list or set, update with its elements
                    current_memory_ids.update(ids)
                else:
                    # For any other type, add as is (string or otherwise)
                    current_memory_ids.add(str(ids))
            
            # Update covered memories
            covered_memory_ids.update(current_memory_ids)
            self.add_event(
                sender=self.name,
                tag=f"covered_memory_ids_{iterations}",
                content=f"Covered memory IDs: {covered_memory_ids}"
            )
            
            # Save tool calls for next iteration
            previous_tool_call = extract_tool_calls_xml(response)
            
            # Check if all memories are covered
            if covered_memory_ids >= all_memory_ids:
                self.add_event(
                    sender=self.name,
                    tag=f"feedback_loop_{iterations}",
                    content="All memories covered in plans"
                )
                break
            
            iterations += 1
            
            if iterations == self._max_consideration_iterations:
                self.add_event(
                    sender=self.name,
                    tag=f"warning_{iterations}",
                    content=f"Reached max iterations "
                            f"({self._max_consideration_iterations}) "
                            "without covering all memories"
                )
        
        # Create a copy of the plans to return
        plans_copy = self.plans.copy()
        
        # Clear the internal plans list
        self.plans = []
        
        return plans_copy

    async def create_user_edit_plan(self, edit: Dict) -> Plan:
        """Create a detailed plan for user-requested edits."""
        # Clear any existing plans before starting
        self.plans = []
        
        if edit["type"] == "ADD":   # ADD
            prompt = await self._get_formatted_prompt(
                "user_add_planner",
                section_path=edit['data']['newPath'],
                section_prompt=edit['data']['sectionPrompt']
            )
        else:  # COMMENT
            prompt = await self._get_formatted_prompt(
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
        
        # Get the latest plan
        latest_plan = self.plans[-1] if self.plans else None
        
        # Clear the internal plans list
        self.plans = []
        
        # Return a copy of the latest plan
        return latest_plan

    async def _get_formatted_prompt(self, prompt_type: str, **kwargs) -> str:
        """
        Format prompt with the appropriate parameters based on prompt type.
        
        Args:
            prompt_type: Type of prompt to format
            **kwargs: Additional parameters specific to the prompt type
        """
        # Create base parameters common to all prompt types
        base_params = {
            "user_portrait": self._session_note \
                .get_user_portrait_str(),
            "biography_structure": json.dumps(
                self.get_biography_structure(), indent=2
            ),
            "biography_content": (await self.biography.export_to_markdown()),
            "style_instructions": BIOGRAPHY_STYLE_PLANNER_INSTRUCTIONS.get(
                self.config.get("biography_style")
            )
        }
        
        # Create specific parameters based on prompt type
        if prompt_type == "add_new_memory_planner":
            missing_memory_ids = kwargs.get('missing_memory_ids', "")
            warning = (
                MISSING_MEMORIES_WARNING.format(
                    previous_tool_call=kwargs.get('previous_tool_call', ""),
                    missing_memory_ids=missing_memory_ids
                ) if missing_memory_ids else ""
            )
            
            prompt_params = {
                **base_params,
                "new_information": '\n\n'.join(
                    [memory.to_xml() for memory in kwargs.get('new_memories', [])]
                ),
                "conversation_summary": self.interview_session.conversation_summary,
                "missing_memories_warning": warning,
                "tool_descriptions": self.get_tools_description(
                    ["add_plan", "propose_follow_up"]),
            }
        elif prompt_type == "user_add_planner":
            prompt_params = {
                **base_params,
                "section_path": kwargs.get('section_path'),
                "section_prompt": kwargs.get('section_prompt'),
                "tool_descriptions": self.get_tools_description(["add_plan"])
            }
        elif prompt_type == "user_comment_planner":
            prompt_params = {
                **base_params,
                "section_title": kwargs.get('section_title'),
                "selected_text": kwargs.get('selected_text'),
                "user_comment": kwargs.get('user_comment'),
                "tool_descriptions": self.get_tools_description(["add_plan"])
            }
        else:
            raise ValueError(f"Unknown prompt type: {prompt_type}")

        # Get and format the prompt template with the parameters
        return get_prompt(prompt_type).format(**prompt_params)

    def _handle_plan_added(self, new_plan: Plan) -> None:
        """Handle adding a new plan, replacing any existing plans for the same section."""
        # Find any existing plans for the same section
        for i, existing_plan in enumerate(self.plans):
            if (
                (new_plan.section_path and \
                 new_plan.section_path == existing_plan.section_path) or
                (new_plan.section_title and \
                 new_plan.section_title == existing_plan.section_title)
            ):
                # Merge memory_ids
                merged_memory_ids = list(set(
                    existing_plan.memory_ids + new_plan.memory_ids
                )) if existing_plan.memory_ids and new_plan.memory_ids \
                      else existing_plan.memory_ids or new_plan.memory_ids

                # Combine update plans if they're different
                merged_update_plan = existing_plan.update_plan
                if new_plan.update_plan and \
                    new_plan.update_plan != existing_plan.update_plan:
                    merged_update_plan = (f"{existing_plan.update_plan}\n\n"
                                          f"{new_plan.update_plan}")

                # Create merged plan with other fields from new plan
                merged_plan = Plan(
                    update_plan=merged_update_plan,
                    status=existing_plan.status,
                    action_type=existing_plan.action_type,
                    memory_ids=merged_memory_ids,
                    section_path=existing_plan.section_path,
                    section_title=existing_plan.section_title,
                )
                
                # Replace the existing plan with merged plan
                self.plans[i] = merged_plan
                return
                
        # If no existing plan was found, append the new one
        self.plans.append(new_plan)