# InterviewSession

## Description
The InterviewSession class is responsible for orchestrating the interview process. It initializes the necessary components, runs the interview, and updates the biography.

## Components
### User: The user that is being interviewed.
- It can be a human or an AI.
### Interviewer: Conducts the interview.
### MemoryManager: Manages the memory of the interviewer and the conversation.
### Biographer: Updates the biography based on the session summary and newly added memories.
### chat_history: The conversation between the interviewer and the user.
- It is a list of messages. Each message has a role (interviewer/user) and a content.
- User and interviewer will get notified when a new message is added to the conversation. (Observer pattern)


## Methods
### run(): Runs the interview session.
### update_biography(session_summary: str): Updates the biography based on the session summary.