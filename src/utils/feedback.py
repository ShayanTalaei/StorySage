import os
import csv
from interview_session.session_models import Message

def save_feedback_to_csv(interviewer_message: Message, feedback_message: Message, user_id: str, session_id: str):
    """Save feedback message to a CSV file with the last conversation message"""

    # Prepare the feedback directory
    feedback_dir = os.path.join(os.getenv("LOGS_DIR", "logs"), user_id, 'feedback')
    os.makedirs(feedback_dir, exist_ok=True)
    feedback_file = os.path.join(feedback_dir, f'session_{session_id}.csv')

    # Create CSV file with headers if it doesn't exist
    if not os.path.exists(feedback_file):
        with open(feedback_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL, escapechar='\\')
            writer.writerow(['timestamp', 'interviewer_message', 'user_feedback'])

    # Clean and prepare the messages
    interviewer_content = interviewer_message.content if interviewer_message else ''
    feedback_content = feedback_message.content if feedback_message else ''
    
    # Append the feedback
    with open(feedback_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL, escapechar='\\')
        writer.writerow([
            feedback_message.timestamp.isoformat(),
            interviewer_content,
            feedback_content
        ])
    