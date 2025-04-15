# StorySage

**StorySage** is a framework that uses AI agents to conduct interviews and write biographies for users 📝

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

Examples:

```bash
# Basic run with just user ID
python src/main.py --user_id john_doe

# Run with voice features enabled
python src/main.py --user_id john_doe --voice_input --voice_output

# Restart a session with user agent
python src/main.py --user_id john_doe --restart --user_agent
```
