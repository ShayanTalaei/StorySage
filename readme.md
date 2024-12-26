# AI Autobiography

📝 The project allows you to create an AI-generated autobiography.

## Setup

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```.env
OPENAI_API_KEY=<your_openai_api_key>
LOGS_DIR="logs"
DATA_DIR="data"
USER_AGENT_PROFILES_DIR="data/sample_user_profiles"
DATABASE_URL="sqlite:///./data/interview_app.db"
```

### Python Dependencies

Install Python dependencies by running:

```bash
pip install -r requirements.txt
```

### PyAudio (optional, for voice features)

To use voice input, you need to install PyAudio. For macOS, you can install PortAudio using Homebrew. Here's how to fix it:

First, install PortAudio using Homebrew:

```bash
brew install portaudio
```

Then, install PyAudio with pip, but we need to specify the path to PortAudio:

```bash
pip install --global-option='build_ext' --global-option='-I/opt/homebrew/include' --global-option='-L/opt/homebrew/lib' pyaudio
```

### Database (optional, for server mode)

Run the database setup script to create the database and tables:

```bash
# Create database and tables (preserves existing data)
python src/main.py --mode setup_db

# Reset database (WARNING: deletes all existing data)
python src/main.py --mode setup_db --reset
```

Note: This will create the database and tables, but **terminal mode doesn't use the database**.

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

Examples:

```bash
# Basic run with just user ID
python src/main.py --user_id john_doe

# Run with voice features enabled
python src/main.py --user_id john_doe --voice_input --voice_output

# Restart a session with user agent
python src/main.py --user_id john_doe --restart --user_agent
```

### Server Mode

Run the interviewer in server mode with:

```bash
python src/main.py --mode server --port 8000
```
