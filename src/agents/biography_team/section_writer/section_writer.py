from typing import Optional, TYPE_CHECKING, List
from dataclasses import dataclass

from agents.biography_team.base_biography_agent import BiographyConfig, BiographyTeamAgent
from agents.biography_team.models import Plan, FollowUpQuestion
from agents.biography_team.section_writer.prompts import get_prompt
from content.biography.biography import Section
from content.biography.biography_styles import BIOGRAPHY_STYLE_WRITER_INSTRUCTIONS
from agents.biography_team.section_writer.tools import (
    UpdateSection, AddSection
)
from agents.shared.note_tools import ProposeFollowUp
from agents.shared.memory_tools import Recall
from agents.shared.feedback_prompts import SECTION_WRITER_TOOL_CALL_ERROR, MISSING_MEMORIES_WARNING
from content.memory_bank.memory import Memory
from utils.llm.xml_formatter import extract_tool_calls_xml

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession

@dataclass
class UpdateResult:
    success: bool
    message: str

class SectionWriter(BiographyTeamAgent):
    def __init__(self, config: BiographyConfig, interview_session: Optional['InterviewSession'] = None):
        super().__init__(
            name="SectionWriter",
            description="Updates individual biography sections based on plans",
            config=config,
            interview_session=interview_session
        )
        self.follow_up_questions: List[FollowUpQuestion] = []
        
        self.tools = {
            "update_section": UpdateSection(biography=self.biography),
            "add_section": AddSection(biography=self.biography),
            "propose_follow_up": ProposeFollowUp(
                on_question_added=lambda q: 
                    self.follow_up_questions.append(q)
            ),
            "recall": Recall(
                memory_bank=self._memory_bank
            )
        }
    
    async def update_section(self, todo_item: Plan) -> UpdateResult:
        """Update a biography section based on a plan."""
        try:
            iterations = 0
            all_memory_ids = set(todo_item.memory_ids)
            covered_memory_ids = set()
            previous_tool_call = None
            tool_call_error = None
            
            while iterations < self._max_consideration_iterations:
                try:
                    prompt = self._get_plan_prompt(
                        todo_item,
                        previous_tool_call=previous_tool_call,
                        missing_memory_ids="\n".join(
                            sorted(list(all_memory_ids - \
                                       covered_memory_ids))
                        ) if previous_tool_call else "",
                        tool_call_error=tool_call_error
                    )
                    
                    self.add_event(
                        sender=self.name, 
                        tag=f"section_write_prompt_{iterations}", 
                        content=prompt
                    )
                    
                    response = await self.call_engine_async(prompt)
                    self.add_event(
                        sender=self.name, 
                        tag=f"section_write_response_{iterations}", 
                        content=response
                    )

                    # Handle tool call
                    try:
                        result = \
                            await self.handle_tool_calls_async(
                                response,
                                raise_error=True
                            )
                        tool_call_error = None
                    except Exception as e:
                        tool_call_error = str(e)
                        self.add_event(
                            sender=self.name,
                            tag="tool_call_error",
                            content=f"Tool call error: {tool_call_error}"
                        )
                        iterations += 1
                        continue

                    # Check if agent wants to proceed with missing memories
                    if "<proceed>yes</proceed>" in response.lower():
                        self.add_event(
                            sender=self.name,
                            tag=f"feedback_loop_{iterations}",
                            content="Agent chose to proceed with missing memories"
                        )
                        return UpdateResult(success=True, 
                                         message="Section updated successfully")

                    if "<recall>" in response:
                        self.add_event(
                            sender=self.name, 
                            tag="recall_response", 
                            content=result
                        )
                        iterations += 1
                        continue

                    # Extract memory IDs from section content in tool calls
                    current_memory_ids = set(
                        Section.extract_memory_ids(response)
                    )
                    covered_memory_ids.update(current_memory_ids)
                        
                    # Save tool calls for next iteration if needed
                    previous_tool_call = extract_tool_calls_xml(response)

                    # Check if all memories are covered
                    if covered_memory_ids >= all_memory_ids or len(all_memory_ids) == 0:
                        self.add_event(
                            sender=self.name,
                            tag=f"feedback_loop_{iterations}",
                            content="All memories covered in section"
                        )                    
                        return UpdateResult(success=True, 
                                            message="Section updated successfully")
                    
                    iterations += 1
                    
                except Exception as e:
                    self.add_event(
                        sender=self.name, 
                        tag="error", 
                        content=f"Error in iteration {iterations}: {str(e)}"
                    )
                    return UpdateResult(success=False, message=str(e))

            return UpdateResult(
                success=False, 
                message="Max iterations reached without covering all memories"
            )
            
        except Exception as e:
            self.add_event(
                sender=self.name, 
                tag="error", 
                content=f"Error in update_section: {str(e)}"
            )
            return UpdateResult(success=False, message=str(e))

    def _get_plan_prompt(self, todo_item: Plan, **kwargs) -> str:
        """Create a prompt for the section writer to update a biography section."""
        try:
            if todo_item.action_type == "user_add":
                events_str = self.get_event_stream_str(
                    filter=[{"sender": self.name, "tag": "recall_response"}]
                )
                return get_prompt("user_add").format(
                    user_portrait=self._session_note \
                        .get_user_portrait_str(),
                    section_path=todo_item.section_path,
                    update_plan=todo_item.update_plan,
                    event_stream=events_str,
                    style_instructions=
                        BIOGRAPHY_STYLE_WRITER_INSTRUCTIONS.get(
                            self.config.get("biography_style", 
                                            "chronological")
                        ),
                    tool_descriptions=self.get_tools_description(
                        ["recall", "add_section"]
                    )
                )
            # Update a section based on user feedback
            elif todo_item.action_type == "user_update":
                events_str = self.get_event_stream_str(
                    filter=[{"sender": self.name, "tag": "recall_response"}]
                )
                curr_section = self.biography.get_section(
                    title=todo_item.section_title
                )
                current_content = curr_section.content if curr_section else ""
                return get_prompt("user_update").format(
                    user_portrait=self._session_note \
                        .get_user_portrait_str(),
                    section_title=todo_item.section_title,
                    current_content=current_content,
                    update_plan=todo_item.update_plan,
                    event_stream=events_str,
                    style_instructions=
                        BIOGRAPHY_STYLE_WRITER_INSTRUCTIONS.get(
                            self.config.get("biography_style", 
                                            "chronological")
                        ),
                    tool_descriptions=self.get_tools_description(
                        ["recall", "update_section"]
                    )
                )
            # Update a section based on newly collected memory
            else:
                # Regular section update based on plan
                curr_section = self.biography.get_section(
                    path=todo_item.section_path \
                        if todo_item.section_path else None,
                    title=todo_item.section_title \
                        if todo_item.section_title else None
                )
                current_content = curr_section.content if curr_section else ""
                
                # Format warning if needed
                missing_memory_ids = kwargs.get('missing_memory_ids', "")
                tool_call_error = kwargs.get('tool_call_error', "")
                
                warning = ""
                if missing_memory_ids:
                    warning = MISSING_MEMORIES_WARNING.format(
                        previous_tool_call=kwargs.get('previous_tool_call', ""),
                        missing_memory_ids=missing_memory_ids
                    )
                
                # Add error warning if there was a tool call error
                if tool_call_error:
                    warning += SECTION_WRITER_TOOL_CALL_ERROR.format(
                        tool_call_error=tool_call_error
                    )
                
                # Create section identifier XML
                if todo_item.section_path:
                    section_identifier_xml = (
                        f"<section_path>\n"
                        f"{todo_item.section_path}\n"
                        f"</section_path>"
                    )
                else:
                    section_identifier_xml = (
                        f"<section_title>\n"
                        f"{todo_item.section_title}\n"
                        f"</section_title>"
                    )
                
                # Format the relevant memories
                relevant_memories = self._memory_bank \
                    .get_formatted_memories_from_ids(
                        todo_item.memory_ids,
                        include_source=True
                    )
                
                return get_prompt("normal").format(
                    user_portrait=self._session_note \
                        .get_user_portrait_str(),
                    section_identifier_xml=section_identifier_xml,
                    current_content=current_content,
                    relevant_memories=relevant_memories,
                    update_plan=todo_item.update_plan,
                    style_instructions=
                        BIOGRAPHY_STYLE_WRITER_INSTRUCTIONS.get(
                            self.config.get("biography_style", 
                                            "chronological")
                        ),
                    tool_descriptions=self.get_tools_description(
                        ["add_section", "update_section", 
                         "propose_follow_up", "recall"]
                    ),
                    missing_memories_warning=warning
                )
        except Exception as e:
            self.add_event(
                sender=self.name, 
                tag="error", 
                content=f"Error in _get_plan_prompt: {str(e)}"
            )
            raise

    async def save_biography(self, is_auto_update: bool=False) -> str:
        """Save the current state of the biography to file."""
        try:
            await self.biography.save(save_markdown=not is_auto_update,
                                       increment_version=not is_auto_update)
            return "Biography saved successfully"
        except Exception as e:
            error_msg = f"Error saving biography: {str(e)}"
            self.add_event(sender=self.name, tag="error", content=error_msg)
            return error_msg

    async def update_biography_baseline(self, new_memories: List[Memory]) -> UpdateResult:
        """Update the biography using the baseline approach with all new memories."""
        try:
            iterations = 0
            tool_call_error = None
            
            while iterations < self._max_consideration_iterations:
                try:
                    # Format all new memories
                    formatted_memories = "\n\n".join([
                        memory.to_xml(
                            include_source=True, 
                            include_memory_info=False
                        ) for memory in new_memories
                    ])
                    
                    # Get the current biography content
                    current_biography = await self.biography.export_to_markdown()
                    
                    # Get user portrait
                    user_portrait = self._session_note \
                        .get_user_portrait_str()
                    
                    # Create error warning if needed
                    error_warning = ""
                    if tool_call_error:
                        error_warning = SECTION_WRITER_TOOL_CALL_ERROR.format(
                            tool_call_error=tool_call_error
                        )
                    
                    # Create the baseline prompt
                    prompt = get_prompt("baseline").format(
                        user_portrait=user_portrait,
                        new_information=formatted_memories,
                        current_biography=current_biography,
                        tool_descriptions=self.get_tools_description(
                            ["add_section", "update_section"]
                        ),
                        error_warning=error_warning
                    )
                    
                    # Call the LLM
                    self.add_event(
                        sender=self.name,
                        tag=f"baseline_prompt_{iterations}",
                        content=prompt
                    )

                    response = await self.call_engine_async(prompt)
                    
                    self.add_event(
                        sender=self.name,
                        tag=f"baseline_response_{iterations}",
                        content=response
                    )

                    # Process tool calls
                    try:
                        await self.handle_tool_calls_async(response, raise_error=True)
                        # If we get here, the tool call was successful
                        return UpdateResult(success=True, 
                                            message="Biography updated with baseline approach")
                    except Exception as e:
                        tool_call_error = str(e)
                        self.add_event(
                            sender=self.name,
                            tag="tool_call_error",
                            content=f"Tool call error: {tool_call_error}"
                        )
                        iterations += 1
                        continue
                
                except Exception as e:
                    self.add_event(
                        sender=self.name,
                        tag="error",
                        content=f"Error in baseline iteration {iterations}: {str(e)}"
                    )
                    return UpdateResult(success=False, message=str(e))
            
            # If we reach here, we've hit the max iterations without success
            return UpdateResult(
                success=False,
                message=f"Max iterations ({self._max_consideration_iterations}) "
                        f"reached without successful update"
            )
        
        except Exception as e:
            self.add_event(
                sender=self.name,
                tag="error",
                content=f"Error in baseline update: {str(e)}"
            )
            return UpdateResult(success=False, message=str(e))
