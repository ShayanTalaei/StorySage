from typing import Type, Optional, Callable, List, Union


from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException
from pydantic import BaseModel, Field, SkipValidation

from agents.biography_team.models import Plan


class AddPlanInput(BaseModel):
    action_type: str = Field(description="Type of action (create/update)")
    section_path: Optional[str] = Field(
        default="",
        description=(
            "Full path to the section. "
            "Required when creating a new section."
            "But either section_path or section_title must be provided."
        )
    )
    section_title: Optional[str] = Field(
        default="",
        description=(
            "Title of the section to update. "
            "Recommended when updating an existing section"
            "But either section_path or section_title must be provided."
        )
    )
    memory_ids: List[str] = Field(
        default=[], 
        description=(
            "Required: A single-line list of quoted memory IDs relevant to this plan, "
            "e.g., ['MEM_03121423_X7K', 'MEM_03121423_X7K']. "
            "Remember to quote the list. Do not separate IDs with commas or spaces. "
            "Format should be a JSON-compatible list with quoted strings: "
            "['MEM_TEMP_1', 'MEM_TEMP_2']"
            "Empty list [] is also acceptable."
        )
    )
    plan_content: str = Field(description="Detailed plan for updating/creating the section")

class AddPlan(BaseTool):
    """Tool for adding a biography update plan."""
    name: str = "add_plan"
    description: str = "Add a plan for updating or creating a biography section"
    args_schema: Type[BaseModel] = AddPlanInput
    on_plan_added: SkipValidation[Callable[[Plan], None]] = Field(
        description="Callback function to be called when a plan is added"
    )

    # def _process_memory_ids(self, memory_ids: Union[List[str], str]) -> List[str]:
    #     """Process memory_ids to ensure it's a list of strings."""
    #     if isinstance(memory_ids, list):
    #         return memory_ids
    #     elif isinstance(memory_ids, str):
    #         # Handle JSON string array
    #         if memory_ids.startswith('[') and memory_ids.endswith(']'):
    #             import json
    #             try:
    #                 return json.loads(memory_ids)
    #             except json.JSONDecodeError:
    #                 pass
    #         # Handle comma-separated string
    #         if ',' in memory_ids:
    #             return [mem_id.strip() for mem_id in memory_ids.split(',')]
    #         # Handle single memory ID
    #         return [memory_ids.strip()]
    #     return []  # Return empty list as default

    def _run(
        self,
        action_type: str,
        plan_content: str,
        section_path: Optional[str] = "",
        section_title: Optional[str] = "",
        memory_ids: Optional[Union[List[str], str]] = [],
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            # processed_memory_ids = self._process_memory_ids(memory_ids or [])
            
            plan = {
                "section_path": section_path,
                "section_title": section_title,
                "memory_ids": memory_ids,
                "plan_content": plan_content
            }
            self.on_plan_added(Plan(**plan))
            return f"Successfully added plan for {section_title or section_path}"
        except Exception as e:
            raise ToolException(f"Error adding plan: {str(e)}")
