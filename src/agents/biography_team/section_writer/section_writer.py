from typing import Optional, TYPE_CHECKING, List, Dict
from dataclasses import dataclass


from agents.biography_team.base_biography_agent import BiographyConfig, BiographyTeamAgent
from agents.biography_team.models import TodoItem
from agents.biography_team.section_writer.prompts import SECTION_WRITER_PROMPT, USER_ADD_SECTION_PROMPT, USER_COMMENT_EDIT_PROMPT
from content.biography.biography_styles import BIOGRAPHY_STYLE_WRITER_INSTRUCTIONS
from agents.biography_team.section_writer.tools import (
    GetSection, GetSectionByTitle, UpdateSection, 
    UpdateSectionByTitle, AddSection, AddFollowUpQuestion, Recall
)

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
        self.follow_up_questions = []
        
        self.tools = {
            "get_section": GetSection(biography=self.biography),
            "get_section_by_title": GetSectionByTitle(biography=self.biography),
            "update_section": UpdateSection(biography=self.biography),
            "update_section_by_title": UpdateSectionByTitle(
                biography=self.biography
            ),
            "add_section": AddSection(biography=self.biography),
            "add_follow_up_question": AddFollowUpQuestion(
                on_question_added=lambda q: self.follow_up_questions.append(q)
            ),
            "recall": Recall(
                memory_bank=self.interview_session.memory_bank if interview_session else None,
                user_id=self.config.get("user_id") if not interview_session else None
            )
        }
    
    async def update_section(self, todo_item: TodoItem) -> UpdateResult:
        """Update a biography section based on a plan."""
        max_iterations = 3
        iterations = 0
        
        while iterations < max_iterations:
            prompt = self._get_prompt(todo_item)
            self.add_event(sender=self.name, tag="section_write_prompt", content=prompt)
            response = await self.call_engine_async(prompt)
            self.add_event(sender=self.name, tag="section_write_response", content=response)
            
            try:
                if "<recall>" in response:
                    # Handle recall response
                    result = self.handle_tool_calls(response)
                    self.add_event(sender=self.name, tag="recall_response", content=result)
                    iterations += 1
                else:
                    # Handle section update
                    self.handle_tool_calls(response)
                    return UpdateResult(success=True, message="Section updated successfully")
                    
            except Exception as e:
                return UpdateResult(success=False, message=str(e))

    def _get_formatted_memories(self, memory_ids: List[str]) -> str:
        """Get and format memories from memory IDs."""
        if not memory_ids:
            return "No relevant memories provided."
            
        memory_texts = []
        for memory_id in memory_ids:
            memory = self.interview_session.memory_bank.get_memory_by_id(memory_id)
            if memory:
                memory_texts.append(memory.to_xml(include_source=True))
        
        return "\n\n".join(memory_texts)

    def _get_prompt(self, todo_item: TodoItem) -> str:
        """Create a prompt for the section writer to update a biography section."""

        # Add a new section based on user feedback
        if todo_item.action_type == "user_add":
            events_str = self.get_event_stream_str(
                filter=[{"sender": self.name, "tag": "recall_response"}]
            )
            return USER_ADD_SECTION_PROMPT.format(
                section_path=todo_item.section_path,
                update_plan=todo_item.update_plan,
                event_stream=events_str,
                style_instructions=BIOGRAPHY_STYLE_WRITER_INSTRUCTIONS.get(
                    self.config.get("biography_style", "chronological")
                ),
                tool_descriptions=self.get_tools_description(["recall", "add_section"])
            )
        # Update a section based on user feedback
        elif todo_item.action_type == "user_update":
            events_str = self.get_event_stream_str(
                filter=[{"sender": self.name, "tag": "recall_response"}]
            )
            current_content = (
                self.tools["get_section_by_title"]._run(todo_item.section_title)
                or "Section does not exist yet."
            )
            return USER_COMMENT_EDIT_PROMPT.format(
                section_title=todo_item.section_title,
                current_content=current_content,
                update_plan=todo_item.update_plan,
                event_stream=events_str,
                style_instructions=BIOGRAPHY_STYLE_WRITER_INSTRUCTIONS.get(
                    self.config.get("biography_style", "chronological")
                ),
                tool_descriptions=self.get_tools_description(
                    ["recall", "update_section_by_title"]
                )
            )
        # Update a section based on newly collected memory
        else:
            section_identifier = todo_item.section_path or todo_item.section_title
            current_content = (
                self.tools["get_section"]._run(section_identifier)
                or "Section does not exist yet."
            )
            return SECTION_WRITER_PROMPT.format(
                section_path=section_identifier,
                update_plan=todo_item.update_plan,
                current_content=current_content,
                relevant_memories=(
                    self._get_formatted_memories(todo_item.memory_ids)
                ),
                style_instructions=BIOGRAPHY_STYLE_WRITER_INSTRUCTIONS.get(
                    self.config.get("biography_style", "chronological")
                ),
                tool_descriptions=self.get_tools_description()
            )

    def save_biography(self, save_markdown: bool = False) -> str:
        """Save the current state of the biography to file."""
        try:
            self.biography.save()
            if save_markdown:
                self.biography.export_to_markdown()
            return "Successfully saved biography to file"
        except Exception as e:
            error_msg = f"Error saving biography: {str(e)}"
            self.add_event(sender=self.name, tag="error", content=error_msg)
            return error_msg
