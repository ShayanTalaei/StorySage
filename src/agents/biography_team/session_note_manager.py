from typing import Dict, List, TYPE_CHECKING
from agents.biography_team.base_biography_agent import BiographyTeamAgent
import xml.etree.ElementTree as ET
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, ToolException
from typing import Type, Optional
from langchain_core.callbacks.manager import CallbackManagerForToolRun

from session_note.session_note import SessionNote

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession

class SessionNoteManager(BiographyTeamAgent):
    def __init__(self, config: Dict, interview_session: 'InterviewSession'):
        super().__init__(
            name="SessionNoteManager",
            description="Updates session notes based on new memories and follow-up questions",
            config=config,
            interview_session=interview_session
        )
        self.session_note = self.interview_session.session_note
        
        self.tools = {
            "update_last_meeting_summary": UpdateLastMeetingSummary(session_note=self.session_note),
            "update_user_portrait": UpdateUserPortrait(session_note=self.session_note),
            "add_interview_question": AddInterviewQuestion(session_note=self.session_note)
        }
        
    async def update_session_note(self, new_memories: List[Dict], follow_up_questions: List[Dict]):
        """Update session notes with new memories and follow-up questions."""
        # Create and log the prompt
        prompt = self._create_session_note_prompt(
            new_memories=new_memories,
            follow_up_questions=follow_up_questions
        )
        self.add_event(sender=self.name, tag="session_note_prompt", content=prompt)
        
        # Get and log the LLM response
        response = self.call_engine(prompt)
        self.add_event(sender=self.name, tag="llm_response", content=response)
        
        # Handle the update
        try:
            self._handle_session_note_update(response)
            self.add_event(
                sender=self.name,
                tag="update_success",
                content="Successfully updated session notes"
            )
        except Exception as e:
            error_msg = f"Error updating session notes: {str(e)}\nResponse: {response}"
            self.add_event(sender=self.name, tag="error", content=error_msg)
            raise

    def _create_session_note_prompt(self, new_memories: List[Dict], follow_up_questions: List[Dict]) -> str:
        return SESSION_NOTE_AGENT_PROMPT.format(
            user_portrait=self.session_note.get_user_portrait_str(),
            last_meeting_summary=self.session_note.get_last_meeting_summary_str(),
            questions_and_notes=self.session_note.get_questions_and_notes_str(),
            new_memories="\n".join([
                f"- {m['text']}"
                for m in new_memories
            ]),
            follow_up_questions="\n".join([
                "<question>\n"
                f"<content>{q['content']}</content>\n"
                f"<context>{q['context']}</context>\n" 
                "</question>"
                for q in follow_up_questions
            ])
        )

    def _handle_session_note_update(self, response: str):
        """Processes the XML response and updates the session note accordingly."""
        if "<session_note_update>" not in response:
            error_msg = "No session_note_update tag found in response"
            self.add_event(sender=self.name, tag="error", content=error_msg)
            return
        
        try:
            start_tag = "<session_note_update>"
            end_tag = "</session_note_update>"
            start_idx = response.find(start_tag)
            end_idx = response.find(end_tag) + len(end_tag)
            
            update_text = response[start_idx:end_idx]
            root = ET.fromstring(update_text)
            
            # Update last meeting summary
            summary_elem = root.find("last_meeting_summary")
            if summary_elem is not None:
                content = summary_elem.find("content")
                if content is not None and content.text:
                    result = self.tools["update_last_meeting_summary"]._run(
                        summary=content.text.strip()
                    )
                    self.add_event(sender=self.name, tag="summary_update", content=result)
            
            # Update user portrait
            portrait_updates = root.find("user_portrait_updates")
            if portrait_updates is not None:
                # Handle updated fields
                for field_update in portrait_updates.findall("field_update"):
                    field_name = field_update.get("name")
                    value_elem = field_update.find("value")
                    if field_name and value_elem is not None and value_elem.text:
                        result = self.tools["update_user_portrait"]._run(
                            field_name=field_name,
                            value=value_elem.text.strip()
                        )
                        self.add_event(sender=self.name, tag="portrait_update", content=result)
                
                # Handle new fields
                for new_field in portrait_updates.findall("new_field"):
                    field_name = new_field.get("name")
                    value_elem = new_field.find("value")
                    if field_name and value_elem is not None and value_elem.text:
                        result = self.tools["update_user_portrait"]._run(
                            field_name=field_name,
                            value=value_elem.text.strip()
                        )
                        self.add_event(sender=self.name, tag="portrait_update", content=result)
            
            # Update questions
            questions_elem = root.find("questions")
            if questions_elem is not None:
                for topic in questions_elem.findall("topic"):
                    topic_name = topic.get("name")
                    if not topic_name:
                        continue
                    
                    for question in topic.findall("question"):
                        question_text = question.text.strip() if question.text else ""
                        if not question_text:
                            continue
                        
                        question_type = question.get("type")
                        question_id = question.get("id")
                        parent_id = question.get("parent_id")
                        
                        # Only add questions marked as new
                        if question_type != "existing":
                            result = self.tools["add_interview_question"]._run(
                                topic=topic_name,
                                question=question_text,
                                question_id=question_id,
                                parent_id=parent_id
                            )
                            self.add_event(sender=self.name, tag="question_update", content=result)
                        
        except Exception as e:
            error_msg = f"Error processing session note update: {str(e)}\nResponse: {response}"
            self.add_event(sender=self.name, tag="error", content=error_msg)
            raise

SESSION_NOTE_AGENT_PROMPT = """\
You are a session note manager, assisting in drafting a user biography. During interviews, we collect new information and follow-up questions suggested by biography experts to delve deeper into the user's background. Your task is to integrate the collected information and questions into the existing session notes, ensuring they are well-organized and ready for the next session. Focus on accuracy, clarity, and completeness in your updates.

Input Context:
<new_memories>
{new_memories}
</new_memories>

<collected_follow_up_questions>
{follow_up_questions}
</collected_follow_up_questions>

<existing_session_notes>
    <user_portrait>
    {user_portrait}
    </user_portrait>

    <last_meeting_summary>
    {last_meeting_summary}
    </last_meeting_summary>

    <questions_and_notes>
    {questions_and_notes}
    </questions_and_notes>
</existing_session_notes>

Core Responsibilities:

1. Write the last meeting summary
   - Summarize key points from new memories
   - Connect new information with existing knowledge
   - Focus on significant revelations or patterns

2. Update the user portrait
- You can either update one field of portrait or create a new field for the portrait.
- If you update one non-empty field of the user portrait:
    * Think carefully about why the original information needs to be changed
    * Explain your reasoning in a <thinking> tag for each field update
    * Example: changing age from "30s" to "35" based on specific memory about birth year
- If you create a new field for the portrait:
    * Consider what important aspects of the user are not yet captured
    * Explain in <thinking> tag why this new field adds value
    * Example: adding "career_transitions" field after learning about job changes

3. Add new follow-up questions
- You only need to include new questions in your output
- For new questions (from two sources):
    * Source 1: Expert-provided follow-up questions in <collected_follow_up_questions>
        - Mark them with type="collected"
        - Remove any duplicate questions from the collected follow-ups
    * Source 2: Your own proposed questions based on:
        - Gaps you identify in the user's story
        - Interesting threads in new memories that need exploration
        - Mark them with type="proposed"
    * For ALL new questions:
        - Choose an appropriate topic category
        - Assign new question ID that doesn't conflict with existing ones
        - Carefully consider parent-child relationships:
            * When to use parent_id:
                - The new question deepens/details an existing question
                - The new question explores a specific aspect of a broader question
                - The new question follows up on a particular point from parent
            * Examples of parent-child relationships:
                - Parent: "Tell me about your education background"
                  Child: "What experiences did you have in university?"
                  Child: "How did your education influence your career choice?"
                
                - Parent: "What was your childhood like?"
                  Child: "Tell me about your relationship with siblings"
                  Child: "What were your favorite activities?"
            * ID Assignment for sub-questions:
                - If parent_id is "6", sub-questions should be "6.1", "6.2", etc.
                - Keep sub-question IDs sequential within their parent
            * When NOT to use parent_id:
                - The question introduces a new, independent topic, which explores breadth rather than depth
                - The question is related but explores a different aspect
                - The question shifts focus to a different time period/theme
- Only include existing questions when:
    * You want to add sub-questions under them
    * Including the parent question helps provide context for the new sub-questions
    * In this case:
        - Mark parent question with type="existing"
        - Use its exact question ID and text
        - Add your new sub-questions after it

Please update the session notes using this XML format:

<session_note_update>
    <last_meeting_summary>
        <content>[Updated meeting summary]</content>
    </last_meeting_summary>

    <user_portrait_updates>
        <field_update name="[field_name]">
            <thinking>
                [Specific reasoning for updating this field:
                 - What new information triggered this update
                 - Why the change is necessary
                 - How it improves accuracy]
            </thinking>
            <value>[updated value]</value>
        </field_update>
        <!-- Repeat for each updated field -->
        
        <new_field name="[field_name]">
            <thinking>
                [Specific reasoning for adding this field:
                 - What information prompted this addition
                 - Why this field is important for the biography
                 - What aspect of the user it captures]
            </thinking>
            <value>[field value]</value>
        </new_field>
        <!-- Repeat for each new field -->
    </user_portrait_updates>
    
    <questions>
        <topic name="[topic_name]">
            <thinking>[Reasoning for question organization]</thinking>
            <question id="[id]" type="existing">[Exact existing question]</question>
            <question id="[id]" type="collected" parent_id="[optional]">[Expert question]</question>
            <question id="[id]" type="proposed" parent_id="[optional]">[Your question]</question>
        </topic>
        <!-- Repeat for each topic -->
    </questions>
</session_note_update>
"""

class UpdateLastMeetingSummaryInput(BaseModel):
    summary: str = Field(description="The new summary text for the last meeting")

class UpdateUserPortraitInput(BaseModel):
    field_name: str = Field(description="The name of the field to update")
    value: str = Field(description="The new value for the field")

class AddInterviewQuestionInput(BaseModel):
    topic: str = Field(description="The topic category for the question")
    question: str = Field(description="The actual question text")
    question_id: str = Field(description="Optional custom ID for the question")
    parent_id: str = Field(description="Optional ID of parent question")

class UpdateLastMeetingSummary(BaseTool):
    """Tool for updating the last meeting summary."""
    name: str = "update_last_meeting_summary"
    description: str = "Updates the last meeting summary in the session note"
    args_schema: Type[BaseModel] = UpdateLastMeetingSummaryInput
    session_note: SessionNote = Field(...)

    def _run(
        self,
        summary: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            self.session_note.last_meeting_summary = summary.strip()
            return "Successfully updated last meeting summary"
        except Exception as e:
            raise ToolException(f"Error updating last meeting summary: {e}")

class UpdateUserPortrait(BaseTool):
    """Tool for updating the user portrait."""
    name: str = "update_user_portrait"
    description: str = "Updates a field in the user portrait"
    args_schema: Type[BaseModel] = UpdateUserPortraitInput
    session_note: SessionNote = Field(...)

    def _format_field_name(self, field_name: str) -> str:
        """Format field name by replacing underscores with spaces and capitalizing words.
        
        Example:
            hobbies_influence -> Hobbies Influence
            early_life_experiences -> Early Life Experiences
        """
        return ' '.join(word.capitalize() for word in field_name.split('_'))

    def _run(
        self,
        field_name: str,
        value: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            formatted_field_name = self._format_field_name(field_name)
            self.session_note.user_portrait[formatted_field_name] = value.strip()
            return f"Successfully updated user portrait field: {formatted_field_name}"
        except Exception as e:
            raise ToolException(f"Error updating user portrait: {e}")

class AddInterviewQuestion(BaseTool):
    """Tool for adding new interview questions."""
    name: str = "add_interview_question"
    description: str = "Adds a new interview question to the session notes"
    args_schema: Type[BaseModel] = AddInterviewQuestionInput
    session_note: SessionNote = Field(...)

    def _run(
        self,
        topic: str,
        question: str,
        question_id: str = None,
        parent_id: str = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            self.session_note.add_interview_question(
                topic=topic,
                question=question,
                question_id=question_id,
                parent_id=parent_id
            )
            return f"Successfully added question to topic: {topic}"
        except Exception as e:
            raise ToolException(f"Error adding interview question: {e}")