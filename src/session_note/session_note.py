import os
import json
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
    
    @classmethod
    def load_from_file(cls, file_path):
        """Loads a SessionNote from a JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Extract the core fields from the file
        user_id = data.pop('user_id', '')
        session_id = data.pop('session_id', '')
        
        # Create new SessionNote instance
        return cls(user_id, session_id, data)
    
    @classmethod
    def initialize_session_note(cls, user_id):
        """Creates a new session note for the first session."""
        session_id = 0
        data = {
            "user_portrait": {
                "Name": "",
                "Age": "",
                "Occupation": "",
                "Location": "",
                "Family Status": "",
                "Interests": [],
                "Background": "",
                "Characteristics": ""
            },
            "last_meeting_summary": "This is the first session with the user. We will start by getting to know them and understanding their background.",
            "question_strings": {
                "General": [
                    "What is your name?",
                    # "How old are you?",
                ],
                # TODO: Ask these questions when user registers
                # "Biography Style": [
                #     "How do you like your biography to be written? e.g. chronological, thematic, etc.",
                #     "Any specific style preferences? e.g. chronological, thematic, etc.",
                # ],
                "Personal": [
                    "Where did you grow up?",
                    "What was your childhood like?"
                ],
                "Professional": [
                    "What do you do for work?",
                    "How did you choose your career path?"
                ],
                # "Interests": [
                #     "What are your main hobbies or interests?",
                #     "What do you like to do in your free time?"
                # ],
                "Relationships": [
                    "Tell me about your family.",
                    "Who are the most important people in your life?"
                ],
                "Life Events": [
                    "What would you say was a defining moment in your life?",
                    "What's one of your most memorable experiences?"
                ],
                # "Future Goals": [
                #     "What are your hopes and dreams for the future?",
                #     "Where do you see yourself in the next few years?"
                # ]
            }
        }
        session_note = cls(user_id, session_id, data)
        session_note.save()
        return session_note
    
    @classmethod
    def get_last_session_note(cls, user_id):
        """Retrieves the last session note for a user."""
        base_path = os.path.join(LOGS_DIR, user_id, "session_notes")
        if not os.path.exists(base_path):
            os.makedirs(base_path)
            
        files = [f for f in os.listdir(base_path) if f.startswith('session_') and f.endswith('.json')]
        if not files:
            return cls.initialize_session_note(user_id)
        
        files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]), reverse=True)
        latest_file = os.path.join(base_path, files[0])
        return cls.load_from_file(latest_file)
    
    def increment_session_id(self):
        """Safely increments the session ID and returns the new value."""
        self.session_id += 1
        return self.session_id
    
    def add_interview_question(self, topic: str, question: str, question_id: str):
        """Adds a new interview question to the session notes.
        
        Args:
            topic: The topic category for the question (e.g. "personal", "professional")
            question: The actual question text
            question_id: Required ID for the question that determines its position:
                - If no period (e.g. "1", "2"): top-level question
                - If has period (e.g. "1.1", "2.3"): sub-question under parent
                The parent ID is extracted from the question_id (e.g. "1" from "1.1")
        
        Example:
            add_interview_question("family", "Tell me about your parents", "1")
            add_interview_question("father_relationship", "How was your relationship with your father?", "1.1")
            add_interview_question("mother_relationship", "What about your mother?", "1.2")
        """
        if not question_id:
            raise ValueError("question_id is required")
        
        if '.' not in question_id:
            # Top-level question
            if topic not in self.topics:
                self.topics[topic] = []
            new_question = InterviewQuestion(topic, question_id, question)
            self.topics[topic].append(new_question)
        else:
            # Sub-question
            parent_id = question_id.rsplit('.', 1)[0]  # e.g., "1.2.3" -> "1.2"
            parent = self.get_question(parent_id)
            
            if not parent:
                raise ValueError(f"Parent question with id {parent_id} not found")
            
            new_question = InterviewQuestion(topic, question_id, question)
            parent.sub_questions.append(new_question)
    
    def delete_interview_question(self, question_id: str):
        """Deletes a question by its ID.
        
        If the question has sub-questions:
        - Clears the question text and notes
        - Keeps the question ID and sub-questions
        
        If the question has no sub-questions:
        - Removes the question completely
        
        Args:
            question_id: The ID of the question to delete (e.g. "1", "1.1", "2.3")
            
        Raises:
            ValueError: If question_id or parent is not found
        """
        # If it's a sub-question, verify parent exists first
        if '.' in question_id:
            parent_id = question_id.rsplit('.', 1)[0]
            parent = self.get_question(parent_id)
            if not parent:
                raise ValueError(f"Parent question with id {parent_id} not found")
        
        # Then check if the question exists
        question = self.get_question(question_id)
        if not question:
            raise ValueError(f"Question with id {question_id} not found")
        
        # If it's a top-level question
        if '.' not in question_id:
            topic = None
            # Find the topic containing this question
            for t, questions in self.topics.items():
                if any(q.question_id == question_id for q in questions):
                    topic = t
                    break
                
            if not topic:
                raise ValueError(f"Topic for question {question_id} not found")
            
            # If it has sub-questions, clear content but keep structure
            if question.sub_questions:
                question.question = ""
                question.notes = []
            else:
                # No sub-questions, remove completely
                self.topics[topic] = [q for q in self.topics[topic] if q.question_id != question_id]
            
        # If it's a sub-question
        else:
            # If it has sub-questions, clear content but keep structure
            if question.sub_questions:
                question.question = ""
                question.notes = []
            else:
                # No sub-questions, remove completely
                def remove_question(questions, target_id):
                    return [q for q in questions if q.question_id != target_id]
                
                parent.sub_questions = remove_question(parent.sub_questions, question_id)
        
    def add_note(self, question_id: str="", note: str=""):
        """Adds a note to a question or the additional notes list."""
        if note:
            if question_id:
                question = self.get_question(question_id)
                if question:
                    question.notes.append(note)
                else:
                    print(f"Question with id {question_id} not found")
            else:
                self.additional_notes.append(note)
        
    def get_question(self, question_id: str):
        """Retrieves an InterviewQuestion object by its ID."""
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
        
    def save(self):
        """Saves the SessionNote to a JSON file."""
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

    def get_user_portrait_str(self) -> str:
        """Returns formatted string of user portrait information."""
        if not self.user_portrait:
            return ""
            
        output = []
        for key, value in self.user_portrait.items():
            output.append(f"{key.replace('_', ' ').title()}: {value}")
        return "\n".join(output)

    def get_last_meeting_summary_str(self) -> str:
        """Returns a formatted string representation of the session note."""
        if not self.last_meeting_summary:
            return ""
        return self.last_meeting_summary
    
    def format_qa(self, qa: InterviewQuestion, hide_answered: str = "") -> list[str]:
        """Formats a question and its sub-questions recursively.
        
        Args:
            qa: InterviewQuestion object to format
            hide_answered: How to display answered questions:
                - "": Show everything (default)
                - "a": Hide answers but show questions
                - "qa": Hide both questions and answers
        
        Raises:
            ValueError: If hide_answered is not one of "", "a", "qa"
        """
        if hide_answered not in ["", "a", "qa"]:
            raise ValueError('hide_answered must be "", "a", or "qa"')
            
        lines = []
        if not qa.question: # Empty question means it is already deleted
            pass
        elif qa.notes:
            if hide_answered == "qa":
                lines.append(f"\n[ID] {qa.question_id}: (Answered)")
            else:
                lines.append(f"\n[ID] {qa.question_id}: {qa.question}")
                if hide_answered != "a":  # Show answers if not hiding them
                    for note in qa.notes:
                        lines.append(f"[note] {note}")
        else:
            # For unanswered questions, always show the question
            lines.append(f"\n[ID] {qa.question_id}: {qa.question}")
        
        if qa.sub_questions:
            for sub_qa in qa.sub_questions:
                lines.extend(self.format_qa(
                    sub_qa,
                    hide_answered=hide_answered
                ))
        return lines

    def get_questions_and_notes_str(self, hide_answered: str = "") -> str:
        """Returns formatted string for questions and notes.
        
        Args:
            hide_answered: How to display answered questions:
                - "": Show everything (default)
                - "a": Hide answers but show questions
                - "qa": Hide both questions and answers
        
        Raises:
            ValueError: If hide_answered is not one of "", "a", "qa"
        """
        if not self.topics:
            return ""
            
        output = []
        
        for topic, questions in self.topics.items():
            output.append(f"\nTopic: {topic}")
            for qa in questions:
                output.extend(self.format_qa(qa, hide_answered=hide_answered))
                
        return "\n".join(output)

    def get_additional_notes_str(self) -> str:
        """Returns formatted string of additional notes."""
        if not self.additional_notes:
            return ""
        return "\n".join(self.additional_notes)

    def clear_questions(self):
        """Clears all questions from the session note, resetting it to an empty state."""
        # Clear all topics and questions
        self.topics = {}
        
        # Clear additional notes
        self.additional_notes = []

    def visualize_topics(self) -> str:
        """Returns a tree visualization of topics and questions.
        
        Example output:
        Topics
        ├── General
        │   └── How old are you?
        ├── Professional
        │   ├── How did you choose your career path?
        │   └── What specific rare plant species did you cultivate?
        │       └── Did you face any challenges?
        └── Personal
            └── Where did you grow up?
        """
        if not self.topics:
            return "No topics"
        
        lines = ["Topics"]
        topics = list(self.topics.items())
        
        def add_question(question: InterviewQuestion, prefix: str, is_last: bool) -> None:
            # Add the current question
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{question.question}")
            
            # Handle sub-questions
            if question.sub_questions:
                new_prefix = prefix + ("    " if is_last else "│   ")
                sub_questions = question.sub_questions
                for i, sub_q in enumerate(sub_questions):
                    add_question(sub_q, new_prefix, i == len(sub_questions) - 1)
        
        # Process each topic
        for topic_idx, (topic, questions) in enumerate(topics):
            # Add topic
            topic_prefix = "└── " if topic_idx == len(topics) - 1 else "├── "
            lines.append(f"{topic_prefix}{topic}")
            
            # Process questions under this topic
            question_prefix = "    " if topic_idx == len(topics) - 1 else "│   "
            for q_idx, question in enumerate(questions):
                add_question(question, question_prefix, q_idx == len(questions) - 1)
        
        return "\n".join(lines)




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