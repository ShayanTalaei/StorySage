#!/bin/bash

# Default values
USER_ID=""
SKIP_BASELINE=false
RESTART=false
MAX_TURNS=20

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --user_id)
      USER_ID="$2"
      shift 2
      ;;
    --max_turns)
      MAX_TURNS="$2"
      shift 2
      ;;
    --skip_baseline)
      SKIP_BASELINE=true
      shift
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
    echo "Usage: ./scripts/run_experiments.sh --user_id <user_id> [--max_turns <turns>] [--skip_baseline] [--restart]"
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Build the command
COMMAND="python ${SCRIPT_DIR}/experiments/run_experiments.py --user_id $USER_ID"
if [ ! -z "$MAX_TURNS" ]; then
  COMMAND="$COMMAND --max_turns $MAX_TURNS"
fi
if [ "$SKIP_BASELINE" = true ]; then
  COMMAND="$COMMAND --skip_baseline"
fi
if [ "$RESTART" = true ]; then
  COMMAND="$COMMAND --restart"
fi

# Print the command
echo "Running command: $COMMAND"

# Run the command
eval "$COMMAND" 