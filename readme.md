## Installation

### Python Dependencies

Install Python dependencies by running:

```bash
pip install -r requirements.txt
```

### PyAudio (for voice features)

To use voice input, you need to install PyAudio. For macOS, you can install PortAudio using Homebrew. Here's how to fix it:

First, install PortAudio using Homebrew:
```bash
brew install portaudio
```

Then, install PyAudio with pip, but we need to specify the path to PortAudio:
```bash
pip install --global-option='build_ext' --global-option='-I/opt/homebrew/include' --global-option='-L/opt/homebrew/lib' pyaudio
```

## Usage

Run the interviewer with:
```bash
python src/main.py --user_id <USER_ID>
```

### Optional Parameters:
- `--user_agent`: Enable user agent mode
- `--voice_output`: Enable voice output
- `--voice_input`: Enable voice input 
- `--restart`: Clear previous session data and restart

### Examples:
```bash
# Basic run with just user ID
python src/main.py --user_id john_doe

# Run with voice features enabled
python src/main.py --user_id john_doe --voice_input --voice_output

# Restart a session with user agent
python src/main.py --user_id john_doe --restart --user_agent
```
