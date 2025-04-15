# StorySage

**StorySage** is a framework that uses AI agents to conduct interviews and write biographies for users 📝

## What is StorySage?

StorySage is an AI-powered interview system that helps capture and preserve personal stories. Through natural conversations, it collects memories, experiences, and life details to create meaningful biographical content. The system uses a team of specialized AI agents that work together to:

1. Conduct engaging interviews with thoughtful questions
2. Remember important details from previous conversations
3. Organize memories into coherent biographical narratives
4. Adapt to each user's unique communication style and interests

As you chat with StorySage, it gradually builds a rich biography that can be shared with family, friends, or kept as a personal record of your life story.

**Key Features**:

- 🤝 Natural conversation flow
- 🧠 Intelligent memory management
- 📚 Structured biography creation
- 🔄 Continuous learning from interactions

## Setup

### Environment Variables

Create a `.env` file in the root directory. Copy the `.env.example` file and fill in the values.

### Python Dependencies

Recommend Python version: 3.12

Install Python dependencies by running:

```bash
pip install -r requirements.txt
```

## Usage

### Terminal Mode

Run the interviewer in terminal mode with:

```bash
python src/main.py --mode terminal --user_id <USER_ID>
```

Optional Parameters:

- `--user_agent`: Enable user agent mode
- `--voice_output`: Enable voice output
- `--voice_input`: Enable voice input
- `--restart`: Clear previous session data and restart

Notes:

- To continue a previous conversation, use the same `--user_id` value as before
- To end a conversation, press Ctrl+C and hit Enter once (don't press multiple times)
- If you use user agent mode, you need to specify the user ID, which is the name of the user profile in the `USER_AGENT_PROFILES_DIR` directory in the `.env` file.
- Once enough memories have been collected (based on `MEMORY_THRESHOLD_FOR_UPDATE`), a biography will be generated and saved in the DATA_DIR directory (e.g., `data/<user_id>/biography_1.json`, `biography_2.json`, etc.)

Examples:

```bash
# Basic run with just user ID
python src/main.py --user_id john_doe

# Run with voice features enabled
python src/main.py --user_id john_doe --voice_input --voice_output

# Restart a session with user agent
python src/main.py --user_id john_doe --restart --user_agent
```

### Biography Output

The biography is the final product of the StorySage system. As you continue conversations with the interviewer, the system:

1. Collects memories and important details about your life
2. Organizes these memories into coherent narrative sections
3. Generates structured biographical content when enough information is gathered

#### Biography Format

Biographies are stored as JSON files in the `data/<user_id>/` directory (e.g., `biography_1.json`, `biography_2.json`). Each file contains:

- Structured sections covering different aspects of your life (childhood, career, relationships, etc.)
- Personal details, values, and perspectives that emerged during interviews

The biography evolves over time as more conversations take place, with newer versions containing more comprehensive and refined content.

#### Accessing Your Biography

You can view your biography by opening the JSON files in the data directory. The system automatically updates these files when enough new memories have been collected (controlled by the `MEMORY_THRESHOLD_FOR_UPDATE` setting).
