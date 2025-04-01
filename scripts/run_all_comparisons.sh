#!/bin/bash

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Default values
RUN_TIMES=5
USER_IDS=()

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --run_times)
            RUN_TIMES="$2"
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
    echo "Usage: ./scripts/run_all_interview_comparisons.sh [--run_times N] <user_id1> [user_id2 ...]"
    exit 1
fi

# Ensure plots directory exists
mkdir -p "$PROJECT_ROOT/plots"

# Function to get max session ID for a user
get_max_session_id() {
    local user_id="$1"
    local exec_logs_dir="logs/$user_id/execution_logs"
    
    if [ ! -d "$exec_logs_dir" ]; then
        echo "0"
        return
    fi
    
    # Find all session directories and get the highest number
    local max_id=0
    for dir in "$exec_logs_dir"/session_*; do
        if [ -d "$dir" ]; then
            # Extract session number from directory name
            local session_num=${dir##*/session_}
            if [ "$session_num" -gt "$max_id" ]; then
                max_id=$session_num
            fi
        fi
    done
    echo "$max_id"
}

# Process each user
for user_id in "${USER_IDS[@]}"; do
    echo "Processing user: $user_id"
    
    # Get max session ID
    max_session=$(get_max_session_id "$user_id")
    
    if [ "$max_session" -eq 0 ]; then
        echo "No sessions found for user $user_id"
        continue
    fi
    
    echo "Found $max_session sessions for user $user_id"
    
    # Process each session's interviews
    for ((session_id=1; session_id<=$max_session; session_id++)); do
        echo "Running interview comparisons for session $session_id..."
        
        # Run comparisons for this session
        COMMAND="${SCRIPT_DIR}/run_single_comparison.sh --session_id $session_id --run_times $RUN_TIMES $user_id"
        echo "Running command: $COMMAND"
        eval "$COMMAND"
        
        echo "Completed session $session_id comparisons"
        echo "-------------------"
    done
    
    # Run the individual user report and save to file
    echo "Generating individual report for user: $user_id"
    USER_REPORT_DIR="$PROJECT_ROOT/plots/$user_id"
    mkdir -p "$USER_REPORT_DIR"
    COMMAND="python ${SCRIPT_DIR}/analysis/comparison_results_aggregated.py --user_ids $user_id"
    echo "Running command: $COMMAND"
    eval "$COMMAND > $USER_REPORT_DIR/comparison_report.txt"
    echo "Individual report saved to: $USER_REPORT_DIR/comparison_report.txt"
    echo "-------------------"
done

# Show final aggregated results only if multiple users are provided
if [ ${#USER_IDS[@]} -gt 1 ]; then
    echo "Generating final aggregated comparison results for all users..."
    COMMAND="python ${SCRIPT_DIR}/analysis/comparison_results_aggregated.py --user_ids ${USER_IDS[@]}"
    echo "Running command: $COMMAND"
    # Save to file
    eval "$COMMAND > $PROJECT_ROOT/plots/comparison_report.txt"
    # Also display in console
    eval "$COMMAND"
    echo "Final report saved to: $PROJECT_ROOT/plots/comparison_report.txt"
fi 