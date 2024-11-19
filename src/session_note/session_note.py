import os
import json
from datetime import datetime
import dotenv

from session_note.interview_question import InterviewQuestion

dotenv.load_dotenv(override=True)

LOGS_DIR = os.getenv("LOGS_DIR")

class SessionNote:
    
    
    def __init__(self, user_id, session_id, data: dict=None):
        self.user_id = user_id
        self.session_id = session_id
        self.user_portrait: dict = data.get("user_portrait", {})
        self.last_meeting_summary: str = data.get("last_meeting_summary", "")
        # Convert raw topic->questions dict into InterviewQuestion objects
        self.topics: dict[str, list[InterviewQuestion]] = {}
        topics = data.get("topics", {})
        if topics:
            def load_question(item):
                question = InterviewQuestion(item["topic"], item["question_id"], item["question"])
                question.notes = item.get("notes", [])
                for sub_q in item.get("sub_questions", []):
                    question.sub_questions.append(load_question(sub_q))
                return question
            for topic, question_items in topics.items():
                self.topics[topic] = [load_question(item) for item in question_items]
        else:
            raw_topics = data.get("question_strings", {})
            question_id = 1
            for topic, questions in raw_topics.items():
                for question in questions:
                    self.add_interview_question(topic, question, question_id=str(question_id))
                    question_id += 1
        self.additional_notes: list[str] = data.get("additional_notes", [])
        
    def add_interview_question(self, topic: str, question: str, question_id: str = None, parent_id: str = None):
        if topic not in self.topics:
            self.topics[topic] = []
            
        if not parent_id:
            # Top-level question
            question_id = question_id if question_id else str(len(self.topics[topic]) + 1)
            new_question = InterviewQuestion(topic, question_id, question)
            self.topics[topic].append(new_question)
        else:
            # Sub-question
            parent = self.get_question(parent_id)
            if parent:
                sub_id = f"{parent_id}.{question_id}" if question_id else f"{parent_id}.{len(parent.sub_questions) + 1}"
                new_question = InterviewQuestion(topic, sub_id, question)
                parent.sub_questions.append(new_question)
            else:
                print(f"Parent question with id {parent_id} not found")
        
    def add_note(self, question_id: str="", note: str=""):
        if note:
            if question_id:
                question = self.get_question(question_id)
                if question:
                    question.notes.append(note)
                else:
                    print(f"Question with id {question_id} not found")
            else:
                self.additional_notes.append(note)
        self.save()
        
    def get_question(self, question_id: str):
        topic = None
        # Find the topic that contains this question
        for t, questions in self.topics.items():
            for q in questions:
                if q.question_id == question_id.split('.')[0]:
                    topic = t
                    break
            if topic:
                break
                
        if not topic:
            return None
            
        if '.' not in question_id:
            # Top-level question
            return next((q for q in self.topics[topic] if q.question_id == question_id), None)
            
        # Navigate through sub-questions
        parts = question_id.split('.')
        current = next((q for q in self.topics[topic] if q.question_id == parts[0]), None)
        
        for part in parts[1:]:
            if not current:
                return None
            current = next((q for q in current.sub_questions if q.question_id.endswith(part)), None)
            
        return current
    
    @classmethod
    def load_from_file(cls, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Extract the core fields from the file
        user_id = data.pop('user_id', '')
        session_id = data.pop('session_id', '')
        
        # Create new SessionNote instance
        return cls(user_id, session_id, data)
        
    def save(self):
        base_path = os.path.join(LOGS_DIR, self.user_id, "session_notes")
        file_path = os.path.join(base_path, f"session_{self.session_id}.json")
        
        if not os.path.exists(base_path):
            os.makedirs(base_path)
            
        # Prepare data for serialization
        data = {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "user_portrait": self.user_portrait,
            "last_meeting_summary": self.last_meeting_summary,
            "additional_notes": self.additional_notes,
            "topics": {}
        }
        
        # Serialize topics and their questions
        for topic, questions in self.topics.items():
            data["topics"][topic] = [q.serialize() for q in questions]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return file_path
    
    @classmethod
    def make_session_1_note(cls, user_id):
        session_id = 1
        data = {
            "user_portrait": {
                "name": "",
                "age": "",
                "occupation": "",
                "location": "",
                "family_status": "",
                "interests": [],
                "background": "",
                "characteristics": ""
            },
            "last_meeting_summary": "This is the first session with the user. We will start by getting to know them and understanding their background.",
            "question_strings": {
                "General": [
                    "What is your name?",
                    "How old are you?",
                ],
                "Biography Style": [
                    "How do you like your biography to be written? e.g. chronological, thematic, etc.",
                    "Any specific style preferences? e.g. chronological, thematic, etc.",
                ],
                "personal": [
                    "Where did you grow up?",
                    "What was your childhood like?"
                ],
                "professional": [
                    "What do you do for work?",
                    "How did you choose your career path?"
                ],
                "interests": [
                    "What are your main hobbies or interests?",
                    "What do you like to do in your free time?"
                ],
                "relationships": [
                    "Tell me about your family.",
                    "Who are the most important people in your life?"
                ],
                "life_events": [
                    "What would you say was a defining moment in your life?",
                    "What's one of your most memorable experiences?"
                ],
                "future_goals": [
                    "What are your hopes and dreams for the future?",
                    "Where do you see yourself in the next few years?"
                ]
            }
        }
        session_note = cls(user_id, session_id, data)
        session_note.save()
        return session_note
    
    @classmethod
    def get_last_session_note(cls, user_id):
        base_path = os.path.join(LOGS_DIR, user_id, "session_notes")
        if not os.path.exists(base_path):
            os.makedirs(base_path)
            
        files = [f for f in os.listdir(base_path) if f.startswith('session_') and f.endswith('.json')]
        if not files:
            return cls.make_session_1_note(user_id)
        
        files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]), reverse=True)
        latest_file = os.path.join(base_path, files[0])
        return cls.load_from_file(latest_file)

    def get_user_portrait_str(self) -> str:
        """Returns formatted string of user portrait information."""
        if not self.user_portrait:
            return ""
            
        output = [
            "\nUser Information:",
            "-" * 20
        ]
        for key, value in self.user_portrait.items():
            output.append(f"{key.replace('_', ' ').title()}: {value}")
        return "\n".join(output)

    def get_last_meeting_summary_str(self) -> str:
        """Returns a formatted string representation of the session note."""
        if not self.last_meeting_summary:
            return ""
            
        output = [
            "\nPrevious Session Summary:",
            "-" * 20,
            self.last_meeting_summary
        ]
        
        return "\n".join(output)
    
    def format_qa(self, qa: InterviewQuestion, prefix="") -> list[str]:
        """Formats a question and its sub-questions recursively."""
        lines = []
        lines.append(f"\n{prefix}: {qa.question}")
        if qa.notes:
            for note in qa.notes:
                lines.append(f"→ {note}")
            
        if qa.sub_questions:
            for sub_qa in qa.sub_questions:
                lines.extend(self.format_qa(sub_qa, f"{prefix}.{qa.question_id}" if prefix else qa.question_id))
        return lines

    def get_questions_and_notes_str(self) -> str:
        """Returns formatted string for questions and notes."""
        if not self.topics:
            return ""
            
        output = [
            "\nInterview Notes:"
        ]
        
        for topic, questions in self.topics.items():
            output.append(f"\nTopic: {topic}")
            for qa in questions:
                output.extend(self.format_qa(qa, qa.question_id))
                
        return "\n".join(output)

    def get_additional_notes_str(self) -> str:
        """Returns formatted string of additional notes."""
        if not self.additional_notes:
            return ""
            
        output = [
            "\nAdditional Notes:",
            self.additional_notes
        ]
        return "\n".join(output)




### EXAMPLE format ###
# Session 1 - January 1, 2024 at 10:00 AM
# --------------------------------------------------

# User Information:
# --------------------
# Name: John Doe
# Age: 30

# Previous Session Summary:
# --------------------
# Last session focused on career goals...

# Interview Notes:
# --------------------

# # Career Goals
# - 1. What are your long-term career aspirations?
#   → Wants to become a senior developer
#   → Interested in leadership roles
# - 1.1. What timeline do you have in mind?
#   → 3-5 years for senior role
# - 1.2. What skills do you need to develop?
# - 2. What challenges are you facing currently?
#   → Time management issues
#   → Technical skill gaps

# # Work-Life Balance
# - 1. How do you manage stress?
# - 2. What's your current work schedule like?
# - 2.1. Are you satisfied with it?
# - 2.2. What would you change?
# - 2.2.1. How would those changes impact your productivity?

# Additional Notes:
# --------------------
# - Follow up on technical training opportunities
# - Schedule monthly check-ins