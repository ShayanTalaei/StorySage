from typing import List

from interview_session.session_models import Message
from utils.llm.engines import get_engine, invoke_engine

CONVERSATION_SUMMARIZE_PROMPT = """
You are an expert conversation summarizer. Your task is to create a concise summary of the recent conversation between an interviewer and a user.

Focus on capturing:
1. Key facts and information shared by the user
2. Important topics discussed
3. Any significant insights or revelations

The summary should be factual, objective, and focused on the content rather than the interaction style.

Recent conversation:
<conversation>
{conversation}
</conversation>

Summarize the key points of this conversation in 100-200 words:
"""

def summarize_conversation(conversation_messages: List[Message]):
    """
    Summarize recent conversation messages.
    
    Args:
        conversation_messages: List of message strings to summarize
        max_length: Maximum number of messages to include
    
    Returns:
        A concise summary of the conversation
    """
    
    
    # Format the conversation
    formatted_conversation = "\n\n".join(
        [f"<{msg.role}>{msg.content}</{msg.role}>" for msg in conversation_messages])
    
    # Create the prompt
    prompt = CONVERSATION_SUMMARIZE_PROMPT.format(conversation=formatted_conversation)
    
    # Get the engine and invoke it
    engine = get_engine(temperature=0.0, max_tokens=1024)
    summary = invoke_engine(engine, prompt)
    
    return summary
