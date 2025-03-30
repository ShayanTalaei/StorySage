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

# Build the commands
CONV_COMMAND="python ${SCRIPT_DIR}/analysis/conversation_stats.py"
BIO_COMMAND="python ${SCRIPT_DIR}/analysis/biography_quality.py"
QUEST_COMMAND="python ${SCRIPT_DIR}/analysis/question_repetition.py"
QUEST_PLOT_COMMAND="python ${SCRIPT_DIR}/analysis/question_repetition_plot.py"
PROG_COMMAND="python ${SCRIPT_DIR}/analysis/biography_progression_plot.py"

# Function to run analysis for a given user ID or list of user IDs
run_analysis() {
    local user_ids="$1"
    local output_file="$2"
    
    # Create directory for output file if it doesn't exist
    mkdir -p "$(dirname "$output_file")"
    
    {
        echo "Analysis Report"
        echo "Generated on: $(date)"
        echo "User IDs analyzed: ${user_ids}"
        echo "----------------------------------------"

        # Run conversation statistics analysis
        echo -e "\nConversation Statistics Analysis:"
        eval "${CONV_COMMAND} --user_ids ${user_ids}"

        # Run biography quality analysis
        echo -e "\nBiography Quality Analysis:"
        eval "${BIO_COMMAND} --user_ids ${user_ids} ${BIO_VERSION}"

        # Run question repetition analysis
        echo -e "\nQuestion Repetition Analysis:"
        eval "${QUEST_COMMAND} --user_ids ${user_ids}"

        # Run question repetition plot analysis
        echo -e "\nQuestion Repetition Plot Analysis:"
        eval "${QUEST_PLOT_COMMAND} --user_ids ${user_ids}"

        # Run biography progression analysis
        echo -e "\nBiography Progression Plot Analysis:"
        eval "${PROG_COMMAND} --user_ids ${user_ids}"

    } 2>&1 | tee "$output_file"

    echo -e "\nAnalysis complete. Results saved to: $output_file"
}

# Handle single vs multiple users
if [ ${#USER_IDS[@]} -eq 1 ]; then
    # Single user case
    OUTPUT_FILE="${SCRIPT_DIR}/../plots/${USER_IDS[0]}/report.txt"
    run_analysis "${USER_IDS[0]}" "$OUTPUT_FILE"
else
    # Multiple users case
    # First run individual analysis for each user
    for user_id in "${USER_IDS[@]}"; do
        echo -e "\nRunning individual analysis for user: $user_id"
        OUTPUT_FILE="${SCRIPT_DIR}/../plots/${user_id}/report.txt"
        run_analysis "$user_id" "$OUTPUT_FILE"
    done
    
    # Then run aggregated analysis for all users
    echo -e "\nRunning aggregated analysis for all users"
    OUTPUT_FILE="${SCRIPT_DIR}/../plots/aggregated_report.txt"
    run_analysis "${USER_IDS[*]}" "$OUTPUT_FILE"
fi 