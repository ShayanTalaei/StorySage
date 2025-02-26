import os
from typing import Optional, TYPE_CHECKING, List
from dataclasses import dataclass


from agents.biography_team.base_biography_agent import BiographyConfig, BiographyTeamAgent
from agents.biography_team.models import Plan, FollowUpQuestion
from agents.biography_team.section_writer.prompts import SECTION_WRITER_PROMPT, USER_ADD_SECTION_PROMPT, USER_COMMENT_EDIT_PROMPT
from content.biography.biography import Section
from content.biography.biography_styles import BIOGRAPHY_STYLE_WRITER_INSTRUCTIONS
from agents.biography_team.section_writer.tools import (
    UpdateSection, AddSection
)
from agents.shared.note_tools import ProposeFollowUp
from agents.shared.memory_tools import Recall
from agents.shared.feedback_prompts import MISSING_MEMORIES_WARNING
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
                memory_bank=self.interview_session.memory_bank \
                            if interview_session else None,
                user_id=self.config.get("user_id") \
                         if not interview_session else None
            )
        }
    
    async def update_section(self, todo_item: Plan) -> UpdateResult:
        """Update a biography section based on a plan."""
        try:
            max_iterations = int(os.getenv(
                "MAX_CONSIDERATION_ITERATIONS", "3"))
            iterations = 0
            all_memory_ids = set(todo_item.memory_ids)
            covered_memory_ids = set()
            previous_tool_call = None
            
            while iterations < max_iterations:
                try:
                    prompt = self._get_prompt(
                        todo_item,
                        previous_tool_call=previous_tool_call,
                        missing_memory_ids="\n".join(
                            sorted(list(all_memory_ids - \
                                       covered_memory_ids))
                        ) if previous_tool_call else ""
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
                    result = await self.handle_tool_calls_async(response)
                    
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
                    if covered_memory_ids >= all_memory_ids:
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

    def _get_prompt(self, todo_item: Plan, **kwargs) -> str:
        """Create a prompt for the section writer to update a biography section."""
        try:
            # Format warning if needed
            missing_memory_ids = kwargs.get('missing_memory_ids', "")
            warning = (
                MISSING_MEMORIES_WARNING.format(
                    previous_tool_call=kwargs.get('previous_tool_call', ""),
                    missing_memory_ids=missing_memory_ids
                ) if missing_memory_ids else ""
            )

            if todo_item.action_type == "user_add":
                events_str = self.get_event_stream_str(
                    filter=[{"sender": self.name, "tag": "recall_response"}]
                )
                return USER_ADD_SECTION_PROMPT.format(
                    user_portrait=self.interview_session.session_note \
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
                return USER_COMMENT_EDIT_PROMPT.format(
                    user_portrait=self.interview_session.session_note \
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
                curr_section = self.biography.get_section(
                    path=todo_item.section_path \
                        if todo_item.section_path else None,
                    title=todo_item.section_title \
                        if todo_item.section_title else None
                )
                current_content = curr_section.content if curr_section else ""
                section_identifier = ""
                if todo_item.section_path:
                    section_identifier = (
                        f"<section_path>"
                        f"{todo_item.section_path}"
                        f"</section_path>"
                    )
                else:
                    section_identifier = (
                        f"<section_title>"
                        f"{todo_item.section_title}"
                        f"</section_title>"
                    )
                return SECTION_WRITER_PROMPT.format(
                    user_portrait=self.interview_session.session_note \
                        .get_user_portrait_str(),
                    section_identifier_xml=section_identifier,
                    update_plan=todo_item.update_plan,
                    current_content=current_content,
                    relevant_memories=(
                        self.interview_session.memory_bank \
                            .get_formatted_memories_from_ids(
                                todo_item.memory_ids,
                                include_source=True
                            )
                    ),
                    missing_memories_warning=warning,
                    style_instructions=
                        BIOGRAPHY_STYLE_WRITER_INSTRUCTIONS.get(
                            self.config.get("biography_style", 
                                            "chronological")
                        ),
                    tool_descriptions=self.get_tools_description(
                        ["add_section", "update_section", 
                         "propose_follow_up", "recall"]
                    )
                )
        except Exception as e:
            self.add_event(
                sender=self.name, 
                tag="error", 
                content=f"Error in _get_prompt: {str(e)}"
            )
            raise

    async def save_biography(self, save_markdown: bool = False) -> str:
        """Save the current state of the biography to file."""
        try:
            await self.biography.save(save_markdown=save_markdown,
                                       increment_version=True)
            return "Biography saved successfully"
        except Exception as e:
            error_msg = f"Error saving biography: {str(e)}"
            self.add_event(sender=self.name, tag="error", content=error_msg)
            return error_msg
