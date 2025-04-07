#!/bin/bash

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Default values
USER_ID=""
NUM_SESSIONS=10
MAX_TURNS=20
RESTART=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --user_id)
            USER_ID="$2"
            shift 2
            ;;
        --num_sessions)
            NUM_SESSIONS="$2"
            shift 2
            ;;
        --max_turns)
            MAX_TURNS="$2"
            shift 2
            ;;
        --restart)
            RESTART=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if user_id is provided
if [ -z "$USER_ID" ]; then
    echo "Error: --user_id is required"
    echo "Usage: ./scripts/run_multiple_sessions.sh --user_id <user_id> [--num_sessions N] [--max_turns M] [--restart]"
    exit 1
fi

echo "Running $NUM_SESSIONS sessions for user $USER_ID"

# Run sessions sequentially
for ((session=1; session<=$NUM_SESSIONS; session++)); do
    echo "Starting session $session of $NUM_SESSIONS..."
    
    # Build the command
    COMMAND="${SCRIPT_DIR}/run_experiments.sh --user_id $USER_ID --max_turns $MAX_TURNS"
    
    # Only use --restart for the first session if restart flag was provided
    if [ "$session" -eq 1 ] && [ "$RESTART" = true ]; then
        COMMAND="$COMMAND --restart"
    fi
    
    echo "Running command: $COMMAND"
    eval "$COMMAND"
    
    echo "Completed session $session"
    echo "==================="
    
    # Add a small delay between sessions
    if [ "$session" -lt "$NUM_SESSIONS" ]; then
        echo "Waiting 5 seconds before starting next session..."
        sleep 5
    fi
done

echo "All $NUM_SESSIONS sessions completed for user $USER_ID" 