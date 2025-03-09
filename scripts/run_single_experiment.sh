#!/bin/bash

# Default values
USER_ID=""
MODEL="gpt-4o"
BASELINE=false
TIMEOUT=10

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
    --timeout)
      TIMEOUT="$2"
      shift 2
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
  echo "Usage: ./scripts/run_single_experiment.sh --user_id <user_id> [--model <model>] [--baseline] [--timeout <minutes>]"
  exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Build the command
COMMAND="python ${SCRIPT_DIR}/run_single_experiment.py --user_id $USER_ID --model $MODEL --timeout $TIMEOUT"
if [ "$BASELINE" = true ]; then
  COMMAND="$COMMAND --baseline"
fi

# Print the command
echo "Running command: $COMMAND"

# Run the command
eval "$COMMAND" 