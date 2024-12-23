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
        prompt = self._create_session_note_prompt(
            new_memories=new_memories,
            follow_up_questions=follow_up_questions
        )
        self.add_event(sender=self.name, tag="prompt", content=prompt)
        response = self.call_engine(prompt)
        self.add_event(sender=self.name, tag="llm_response", content=response)
        
        # Handle the update
        try:
            self._handle_session_note_update(response)
            self.add_event(
                sender=self.name,
                tag="event_result",
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
            questions_and_notes=self.session_note.get_questions_and_notes_str(hide_answered="a"),
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
                    self.add_event(sender=self.name, tag="event_result", content=result)
            
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
                        self.add_event(sender=self.name, tag="event_result", content=result)
                
                # Handle new fields
                for field_create in portrait_updates.findall("field_create"):
                    field_name = field_create.get("name")
                    value_elem = field_create.find("value")
                    if field_name and value_elem is not None and value_elem.text:
                        result = self.tools["update_user_portrait"]._run(
                            field_name=field_name,
                            value=value_elem.text.strip()
                        )
                        self.add_event(sender=self.name, tag="event_result", content=result)
            
            # Update questions
            questions_elem = root.find("questions")
            if questions_elem is not None:
                for topic in questions_elem.findall("topic"):
                    topic_name = topic.get("name")
                    if not topic_name:
                        continue
                    
                    # Handle independent questions (no parent)
                    for question in topic.findall("question"):
                        question_text = question.text.strip() if question.text else ""
                        if not question_text or question.get("type") == "existing":
                            continue
                            
                        result = self.tools["add_interview_question"]._run(
                            topic=topic_name,
                            question=question_text,
                            question_id=question.get("id")
                        )
                        self.add_event(sender=self.name, tag="event_result", content=result)
                    
                    # Handle question groups (parent with sub-questions)
                    for group in topic.findall("question_group"):
                        parent = group.find("parent")
                        if parent is None or not parent.text:
                            continue
                            
                        sub_questions = group.find("sub_questions")
                        if sub_questions is None:
                            continue
                            
                        for question in sub_questions.findall("question"):
                            question_text = question.text.strip() if question.text else ""
                            if not question_text:
                                continue
                                
                            result = self.tools["add_interview_question"]._run(
                                topic=topic_name,
                                question=question_text,
                                question_id=question.get("id")
                            )
                            self.add_event(sender=self.name, tag="event_result", content=result)
            
        except Exception as e:
            error_msg = f"Error processing session note update: {str(e)}\nResponse: {response}"
            self.add_event(sender=self.name, tag="error", content=error_msg)
            raise

SESSION_NOTE_AGENT_PROMPT = """\
<session_note_manager_persona>
You are a session note manager, assisting in drafting a user biography. During interviews, we collect new information/memories from the user and follow-up questions from biography experts to delve deeper into the user's background. Your task is to integrate the collected follow-up questions into the existing session notes, write the meeting summary, and update the user portrait. These notes guide the interviewer in future sessions, helping them track covered topics and identify areas needing exploration.
</session_note_manager_persona>

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
<core_responsibilities>
1. Write the last meeting summary
- Summarize key points from new memories
- Connect new information with existing knowledge
- Focus on significant revelations or patterns

2. Update the user portrait
- You can either update one field of portrait or create a new field for the portrait.
- If you update one non-empty field of the user portrait:
    * Use <field_update> tag for each field update
    * Think carefully about why the original information needs to be changed and explain your reasoning in a <thinking> tag for each field update
    * Example: changing age from "30s" to "35" based on specific memory about birth year
- For creating new fields in the portrait:
    * Use <field_create> tag for each field creation
    * Think carefully about why the new field is important and explain your reasoning in a <thinking> tag for each field creation
    * Be very selective - only add fundamental, high-level aspects of the user
    * The portrait should capture core characteristics, not specific details
    * It's perfectly fine to make NO additions if existing fields are sufficient
    * Good examples of portrait fields:
        - "Career Path": "Software Engineer turned Entrepreneur"
        - "Life Philosophy": "Believes in continuous learning and giving back"
        - "Core Values": "Family, Education, Innovation"
    * Avoid adding detailed or narrow fields like:
        - "Gardening Techniques" (too specific)
        - "College Projects" (too detailed)
        - "Daily Routine" (too granular)
    * If a detail is important, it should go into the biography sections instead

3. Add new follow-up questions
A. Question Sources:
   - Source 1: Expert-provided follow-up questions in <collected_follow_up_questions></collected_follow_up_questions> tags
       * Mark them with type="collected"
   - Source 2: Your own proposed questions based on:
       * Gaps you identify in the user's story
       * Interesting threads in new memories that need exploration
       * Mark them with type="proposed"

B. Question Organization:
    B.1. Parent-Child Relationships:
      - When to create sub-questions:
          * To deepen/detail an existing question
          * To explore a specific aspect of a broader question
          * To follow up on a particular point from parent
      - When NOT to create sub-questions:
          * For new, independent topics (exploring breadth rather than depth)
          * When exploring a different aspect or time period
          * When shifting focus to a different theme

    B.2. ID Assignment:
      - For sub-questions:
          * Parent ID MUST come first: if parent is "6", use "6.1", "6.2", etc.
          * Keep sub-question IDs sequential within their parent
      - For new top-level questions:
          * Use next available number in the topic

    B.3. Including Existing Parent Questions:
      - When to include:
          * When adding sub-questions under the parent question
          * To provide context for the new sub-questions
      - How to include:
          * Mark with type="existing"
          * Use exact question ID and text
          * Place before its new sub-questions

C. Question Content Requirements:
    - Always phrase questions directly to the user using "you/your"
    - Examples:
        ✓ "What motivated you to start your own business?"
        ✓ "How did your childhood experiences shape your career choice?"
        ✗ "What motivated the user to start their business?"
        ✗ "How did their childhood experiences shape their career?"
</core_responsibilities>

Please update the session notes using this XML format:

<session_note_update>
    <last_meeting_summary>
        <content>[Updated meeting summary]</content>
    </last_meeting_summary>

    <user_portrait_updates>
        <field_update name="[field_name]">
            <thinking>[Clear reasoning for update]</thinking>
            <value>[Updated information]</value>
        </field_update>
        <!-- Repeat for each updated field -->
        
        <field_create name="[field_name]">
            <thinking>[Clear reasoning for addition]</thinking>
            <value>[New information]</value>
        </field_create>
        <!-- Repeat for each new field -->
    </user_portrait_updates>
    
    <questions>
        <!-- Example of organizing questions in a topic -->
        <topic name="[topic_name]">
            <thinking>Adding depth to university experience and its impact</thinking>
            
            <!-- Independent questions (no parent) -->
            <question id="4" type="collected">What continuing education have you pursued?</question>
            <!-- Repeat for each independent question -->
            
            <!-- Question group with parent and its sub-questions -->
            <question_group>
                <!-- Parent question must be included and marked as existing -->
                <parent type="existing" id="3">Tell me about your university years</parent>
                <!-- Sub-questions under this parent -->
                <sub_questions>
                    <question id="3.1" type="collected">What extracurricular activities were most meaningful?</question>
                    <question id="3.2" type="proposed">How did these experiences shape your career choice?</question>
                </sub_questions>
            </question_group>
            <!-- Repeat for each for each question group -->
        </topic>
        <!-- Repeat for each topic -->
    </questions>
</session_note_update>

Important Notes about Questions XML Format:
<format_notes>
1. For independent questions (no parent):
   - Place directly under <topic>
   - Do not include parent_id
   - Use next available number in topic for id

2. For sub-questions:
   - Must use <question_group> structure
   - Must include parent question with exact ID and text
   - All questions in <sub_questions> automatically use parent's ID as prefix
   - Keep sub-question IDs sequential (e.g., 3.1, 3.2)

3. Question types:
   - type="existing": For parent questions that already exist
   - type="collected": For questions from follow-up questions list
   - type="proposed": For your own suggested questions

Example Organization of Questions:
<topic name="Education">
    <thinking>Adding depth to university experience and its impact</thinking>
    
    <!-- Independent questions (no parent) -->
    <question id="4" type="collected">What continuing education have you pursued?</question>
    
    <!-- Question group with parent and its sub-questions -->
    <question_group>
        <!-- Parent question must be included and marked as existing -->
        <parent type="existing" id="3">Tell me about your university years</parent>
        <!-- Sub-questions under this parent -->
        <sub_questions>
            <question id="3.1" type="collected">What extracurricular activities were most meaningful?</question>
            <question id="3.2" type="proposed">How did these experiences shape your career choice?</question>
        </sub_questions>
    </question_group>
</topic>

</format_notes>
"""

class UpdateLastMeetingSummaryInput(BaseModel):
    summary: str = Field(description="The new summary text for the last meeting")

class UpdateUserPortraitInput(BaseModel):
    field_name: str = Field(description="The name of the field to update")
    value: str = Field(description="The new value for the field")

class AddInterviewQuestionInput(BaseModel):
    topic: str = Field(description="The topic category for the question")
    question: str = Field(description="The actual question text")
    question_id: str = Field(description="The ID that determines question position (e.g. '1' for top-level, '1.1' for sub-question)")

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
        """Format field name by capitalizing words, handling both spaces and underscores as delimiters.
        
        Examples:
            hobbies_influence -> Hobbies Influence
            early life_experiences -> Early Life Experiences
            Career Goals -> Career Goals
            family_Life History -> Family Life History
        """
        # First split by underscores, then by spaces
        words = []
        for part in field_name.split('_'):
            words.extend(part.split())
        
        # Capitalize first letter of each word
        return ' '.join(word.capitalize() for word in words)

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
        question_id: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            self.session_note.add_interview_question(
                topic=topic,
                question=question,
                question_id=question_id
            )
            return f"Successfully added question to topic: {topic}"
        except Exception as e:
            raise ToolException(f"Error adding interview question: {e}")