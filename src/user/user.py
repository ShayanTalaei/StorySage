from interview_session.session_models import Participant, Message
from utils.logger import SessionLogger

GREEN = '\033[92m'
ORANGE = '\033[93m'
RESET = '\033[0m'

class User(Participant):
    def __init__(self, user_id: str, interview_session):
        super().__init__(title="User", interview_session=interview_session)
        self.user_id = user_id
        SessionLogger.log_to_file("execution_log", f"User object for {user_id} has been created.")
        
    async def on_message(self, message: Message):
        self.show_last_message_history(message)
        user_response = input(f"{ORANGE}User: {RESET}")
        self.interview_session.add_message_to_chat_history(self.title, user_response)
        
    def show_last_message_history(self, message: Message):
        print(f"{message.role}: {message.content}")