#!/bin/bash

# Default values
USER_ID=""
MODEL="gpt-4o"
BASELINE=false
RESTART=false
MAX_TURNS=30

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --user_id)
      USER_ID="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --baseline)
      BASELINE=true
      shift
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
  echo "Usage: ./scripts/run_single_experiment.sh --user_id <user_id> [--model <model>] [--baseline] [--max_turns <turns>] [--restart]"
  exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Build the command
COMMAND="python ${SCRIPT_DIR}/experiments/run_single_experiment.py --user_id $USER_ID --model $MODEL"
if [ ! -z "$MAX_TURNS" ]; then
  COMMAND="$COMMAND --max_turns $MAX_TURNS"
fi
if [ "$BASELINE" = true ]; then
  COMMAND="$COMMAND --baseline"
fi
if [ "$RESTART" = true ]; then
  COMMAND="$COMMAND --restart"
fi

# Print the command
echo "Running command: $COMMAND"

# Run the command
eval "$COMMAND" 