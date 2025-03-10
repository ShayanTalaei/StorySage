#!/bin/bash

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if at least one user ID is provided
if [ $# -eq 0 ]; then
    echo "Error: At least one user ID is required"
    echo "Usage: ./scripts/analyze_results.sh <user_id1> [user_id2 ...]"
    exit 1
fi

# Build the commands
CONV_COMMAND="python ${SCRIPT_DIR}/analysis/conversation_stats.py --user_ids $@"
BIO_COMMAND="python ${SCRIPT_DIR}/analysis/biography_quality.py --user_ids $@"
COMP_COMMAND="python ${SCRIPT_DIR}/analysis/comparison_results.py --user_ids $@"
QUEST_COMMAND="python ${SCRIPT_DIR}/analysis/question_repetition.py --user_ids $@"

# Run conversation statistics analysis
echo "Running conversation statistics analysis..."
eval "$CONV_COMMAND"

# Run biography quality analysis
echo -e "\nRunning biography quality analysis..."
eval "$BIO_COMMAND"

# Run comparison results analysis
echo -e "\nRunning comparison results analysis..."
eval "$COMP_COMMAND"

# Run question repetition analysis
echo -e "\nRunning question repetition analysis..."
eval "$QUEST_COMMAND" 