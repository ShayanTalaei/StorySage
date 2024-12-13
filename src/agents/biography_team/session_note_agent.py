from typing import Dict, List, TYPE_CHECKING
from agents.biography_team.base_biography_agent import BiographyTeamAgent
from agents.memory_manager.memory_manager import UpdateSessionNote
import xml.etree.ElementTree as ET

if TYPE_CHECKING:
    from interview_session.interview_session import InterviewSession

# TODO-lmj: we should write tools to update the session note rather then using self.session_note directly.
class SessionNoteAgent(BiographyTeamAgent):
    def __init__(self, config: Dict, interview_session: 'InterviewSession'):
        super().__init__(
            name="SessionNoteAgent",
            description="Updates session notes based on new memories and follow-up questions",
            config=config,
            interview_session=interview_session
        )
        self.session_note = self.interview_session.session_note
        self.tools = {
            "update_session_note": UpdateSessionNote(session_note=self.session_note)
        }
        
    async def update_session_note(self, new_memories: List[Dict], follow_up_questions: List[Dict]):
        memory_log = "\n".join(f"Memory {i+1}: {memory}" for i, memory in enumerate(new_memories))
        question_log = "\n".join(f"Question {i+1}: {question}" for i, question in enumerate(follow_up_questions))
        
        self.add_event(sender=self.name, tag="update_session_note", content=f"Updating session note with {len(new_memories)} new memories: {memory_log} and {len(follow_up_questions)} follow-up questions: {question_log}")
        
        return
        prompt = self._create_session_note_prompt(
            new_memories=new_memories,
            follow_up_questions=follow_up_questions
        )
        response = self.call_engine(prompt)
        self._handle_session_note_update(response) 

    def _create_session_note_prompt(self, new_memories: List[Dict], follow_up_questions: List[Dict]) -> str:
        return SESSION_NOTE_MESSAGE.format(
            current_notes=self.session_note.to_str(),
            memories_text="\n".join([f"Memory: {m['text']}" for m in new_memories]),
            questions_text="\n".join([
                f"- {q['question']} (Type: {q['type']})" 
                for q in follow_up_questions
            ]),
            tool_descriptions=self.get_tools_description()
        )

    def _handle_session_note_update(self, response: str):
        if "<session_note_update>" in response:
            update_text = response[response.find("<session_note_update>"): response.find("</session_note_update>") + 20]
            root = ET.fromstring(update_text)
            
            # Update user portrait
            user_portrait = root.find("user_portrait")
            if user_portrait is not None and user_portrait.text:
                self.session_note.user_portrait = user_portrait.text.strip()
            
            # Update last meeting summary
            summary = root.find("last_meeting_summary")
            if summary is not None and summary.text:
                self.session_note.last_meeting_summary = summary.text.strip()
            
            # Update questions
            for topic in root.find("questions").findall("topic"):
                topic_name = topic.get("name")
                for question in topic.findall("question"):
                    self.session_note.add_interview_question(
                        topic=topic_name,
                        question=question.text.strip()
                    )
            
            # Save the updated session note
            self.session_note.save() 

SESSION_NOTE_MESSAGE = """\
You are a session note manager. Your task is to update the session notes based on new information and prepare questions for the next session.

Current Session Notes:
{current_notes}

New Memories:
{memories_text}

Suggested Follow-up Questions:
{questions_text}

Available Tools:
{tool_descriptions}

Please update the session notes and organize the questions for the next session.

Provide your response in the following XML format:
<session_note_update>
    <user_portrait>
        Updated user portrait information
    </user_portrait>
    <last_meeting_summary>
        Summary of the latest session
    </last_meeting_summary>
    <questions>
        <topic name="Topic Name">
            <question>Question text</question>
            ...
        </topic>
        ...
    </questions>
</session_note_update>
""" 