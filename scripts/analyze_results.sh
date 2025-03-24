#!/bin/bash

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Parse arguments
BIO_VERSION=""
USER_IDS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --bio_version)
            BIO_VERSION="--bio_version $2"
            shift 2
            ;;
        *)
            USER_IDS+=("$1")
            shift
            ;;
    esac
done

# Check if at least one user ID is provided
if [ ${#USER_IDS[@]} -eq 0 ]; then
    echo "Error: At least one user ID is required"
    echo "Usage: ./scripts/analyze_results.sh [--bio_version VERSION] <user_id1> [user_id2 ...]"
    exit 1
fi

# Convert user IDs array to space-separated string
USER_IDS_STR="${USER_IDS[@]}"

# Build the commands
CONV_COMMAND="python ${SCRIPT_DIR}/analysis/conversation_stats.py --user_ids ${USER_IDS_STR}"
BIO_COMMAND="python ${SCRIPT_DIR}/analysis/biography_quality.py --user_ids ${USER_IDS_STR} ${BIO_VERSION}"
QUEST_COMMAND="python ${SCRIPT_DIR}/analysis/question_repetition.py --user_ids ${USER_IDS_STR}"
LATENCY_COMMAND="python ${SCRIPT_DIR}/analysis/latency_plot.py --user_ids ${USER_IDS_STR}"
QUEST_PLOT_COMMAND="python ${SCRIPT_DIR}/analysis/question_repetition_plot.py --user_ids ${USER_IDS_STR}"
PROG_COMMAND="python ${SCRIPT_DIR}/analysis/biography_progression_plot.py --user_ids ${USER_IDS_STR}"

# Run conversation statistics analysis
echo "Running conversation statistics analysis..."
eval "$CONV_COMMAND"

# Run biography quality analysis
echo -e "\nRunning biography quality analysis..."
eval "$BIO_COMMAND"

# Run question repetition analysis
echo -e "\nRunning question repetition analysis..."
eval "$QUEST_COMMAND"

# Run latency analysis
echo -e "\nRunning latency analysis..."
eval "$LATENCY_COMMAND"

# Run question repetition plot analysis
echo -e "\nRunning question repetition plot analysis..."
eval "$QUEST_PLOT_COMMAND"

# Run biography progression analysis
echo -e "\nRunning biography progression analysis..."
eval "$PROG_COMMAND" 