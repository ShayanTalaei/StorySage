import os
import json
import argparse
from typing import List, Dict
import sys
from pathlib import Path

# Add src directory to Python path
src_dir = str(Path(__file__).parent.parent)
if src_dir not in sys.path:
    sys.path.append(src_dir)

from utils.llm.engines import get_engine, invoke_engine
from utils.llm.xml_formatter import extract_tool_arguments

class TopicExtractor:
    def __init__(self, profile_dir: str):
        """
        Initialize the TopicExtractor with the directory containing user profiles.
        
        Args:
            profile_dir: Path to directory containing user profile folders
        """
        self.profile_dir = profile_dir
        
    def extract_topics(self, user_id: str) -> None:
        """
        Extract topics from a user's profile and save them to a topics file.
        
        Args:
            user_id: ID of the user whose profile to process
        """
        # Verify user directory exists
        user_dir = os.path.join(self.profile_dir, user_id)
        if not os.path.isdir(user_dir):
            raise ValueError(f"User directory not found: {user_dir}")

        # Read the user's profile
        profile_path = os.path.join(user_dir, f"{user_id}.md")
        if not os.path.exists(profile_path):
            raise ValueError(f"Profile file not found: {profile_path}")

        with open(profile_path, 'r') as f:
            profile_content = f.read()
            
        # Get topics using LLM
        topics = self._get_topics_from_llm(profile_content)
        
        # Create topics data structure
        topics_data = {
            "topics": topics,
            "current_index": 0
        }
        
        # Save to topics file
        topics_path = os.path.join(user_dir, "topics.json")
        with open(topics_path, 'w') as f:
            json.dump(topics_data, f, indent=2)
            
    def _get_topics_from_llm(self, profile_content: str) -> List[Dict[str, str]]:
        """
        Use LLM to extract topics from profile content.
        
        Args:
            profile_content: The content of the user's profile
            
        Returns:
            List of topic dictionaries with 'title' and 'description' keys
        """
        prompt = self._create_topic_extraction_prompt(profile_content)
        
        # Get LLM response
        engine = get_engine("gpt-4o-mini")
        response = invoke_engine(engine, prompt)
        
        # Extract topics from XML response
        topics = []
        titles = extract_tool_arguments(response, "extract_topic", "title")
        descriptions = extract_tool_arguments(
                            response, "extract_topic", "description")
        
        # Pair up titles and descriptions
        for title, description in zip(titles, descriptions):
            if title and description:
                topics.append({
                    "title": title,
                    "description": description
                })
        
        if not topics:
            print("Error: Failed to extract valid topics from LLM response")
        return topics
            
    def _create_topic_extraction_prompt(self, profile_content: str) -> str:
        """
        Create the prompt for topic extraction.
        
        Args:
            profile_content: The content of the user's profile
            
        Returns:
            Formatted prompt string
        """
        return f"""
Please analyze this biographical profile and extract distinct topics that could be discussed in separate interview sessions. For each topic, provide a brief description.

Profile content:
<profile_content>
{profile_content}
</profile_content>

For each topic you identify, make a separate tool call with the topic title and description. The title should be 2-5 words and the description should be 1-2 sentences.

Please identify 10 major topics that would make for meaningful interview segments. Avoid overlapping topics and ensure each topic is distinct enough to warrant its own discussion.

Make a separate <extract_topic> tool call for each topic you identify, with both <title> and <description> tags. Wrap all tool calls in <tool_calls>..</tool_calls> tags.

Example format:
<tool_calls>
    <extract_topic>
        <title>Early Education</title>
        <description>Experiences in elementary and middle school, including influential teachers and early academic interests.</description>
    </extract_topic>
    <extract_topic>
        <title>Family Publishing Business</title>
        <description>Involvement with father's Black Classic Press and its influence on early exposure to literature.</description>
    </extract_topic>
    ....
</tool_calls>
"""

def main():
    """
    Main function to run the topic extraction process.

    Example usage:
    python src/utils/topic_extractor.py --user_id coates
    python -m src.utils.topic_extractor --user_id coates
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Extract topics from user profiles')
    parser.add_argument('--user_id', type=str, help='Specific user ID to process. '
                        'If not provided, processes all users.')
    args = parser.parse_args()

    # Get profile directory from environment variable
    profile_dir = os.getenv("USER_AGENT_PROFILES_DIR")
    if not profile_dir:
        raise ValueError("USER_AGENT_PROFILES_DIR environment variable not set")
        
    extractor = TopicExtractor(profile_dir)
    
    if args.user_id:
        # Process specific user
        try:
            print(f"Extracting topics for user: {args.user_id}")
            extractor.extract_topics(args.user_id)
            print(f"Completed topic extraction for {args.user_id}")
        except ValueError as e:
            print(f"Error processing user {args.user_id}: {str(e)}")
    else:
        # Process all users
        for user_id in os.listdir(profile_dir):
            if os.path.isdir(os.path.join(profile_dir, user_id)):
                try:
                    print(f"Extracting topics for user: {user_id}")
                    extractor.extract_topics(user_id)
                    print(f"Completed topic extraction for {user_id}")
                except ValueError as e:
                    print(f"Error processing user {user_id}: {str(e)}")
                    continue

if __name__ == "__main__":
    main() 