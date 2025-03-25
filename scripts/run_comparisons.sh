#!/bin/bash

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Default values
RUN_TIMES=5
SESSION_ID=""  # No default - let Python scripts handle defaults
COMPARISON_TYPE="all"  # Default to running both types

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --run_times)
            RUN_TIMES="$2"
            shift 2
            ;;
        --session_id)
            SESSION_ID="$2"
            shift 2
            ;;
        --type)
            COMPARISON_TYPE="$2"
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
    echo "Usage: ./scripts/run_comparisons.sh [--run_times N] [--session_id S] [--type all|bio|interview] <user_id1> [user_id2 ...]"
    exit 1
fi

# Validate comparison type
if [[ "$COMPARISON_TYPE" != "all" && "$COMPARISON_TYPE" != "bio" && "$COMPARISON_TYPE" != "interview" ]]; then
    echo "Error: Invalid comparison type. Must be 'all', 'bio', or 'interview'"
    echo "Usage: ./scripts/run_comparisons.sh [--run_times N] [--session_id S] [--type all|bio|interview] <user_id1> [user_id2 ...]"
    exit 1
fi

# Function to count rows in CSV (excluding header)
count_csv_rows() {
    local file="$1"
    if [ -f "$file" ]; then
        # Subtract 1 to exclude header row
        echo $(($(wc -l < "$file") - 1))
    else
        echo 0
    fi
}

# Function to count session-specific comparisons
count_session_comparisons() {
    local file="$1"
    local session_id="$2"
    if [ ! -f "$file" ]; then
        echo 0
        return
    fi
    # Use awk to count rows where "Session ID" column matches session_id
    # Skip header row (-F, for CSV) and count matching rows
    awk -F, -v sid="$session_id" '
        NR==1 { for (i=1; i<=NF; i++) if ($i=="Session ID") col=i }
        NR>1 { if ($col==sid) count++ }
        END { print count+0 }
    ' "$file"
}

# Add function to count baseline models
count_baseline_models() {
    local count=0
    for dir in logs_*; do
        if [ -d "$dir" ]; then
            ((count++))
        fi
    done
    echo $count
}

# Run evaluations multiple times for each user
for user_id in "${USER_IDS[@]}"; do
    echo "Running evaluations for user: $user_id"
    if [ -n "$SESSION_ID" ]; then
        echo "Using session ID: $SESSION_ID (and same version for biography)"
    fi
    
    # Get number of baseline models
    NUM_BASELINES=$(count_baseline_models)
    if [ $NUM_BASELINES -eq 0 ]; then
        echo "Error: No baseline models found (no logs_* directories)"
        exit 1
    fi
    
    # Calculate total needed comparisons
    TOTAL_NEEDED=$((RUN_TIMES * NUM_BASELINES))
    echo "Found $NUM_BASELINES baseline models, need $TOTAL_NEEDED total comparisons"
    
    # Check existing comparison counts
    bio_comparisons=0
    interview_comparisons=0
    
    # For biography comparisons, check version-specific directory
    if [ -n "$SESSION_ID" ]; then
        bio_csv="logs/$user_id/evaluations/biography_$SESSION_ID/biography_comparisons.csv"
        bio_comparisons=$(count_csv_rows "$bio_csv")
    else
        bio_csv="logs/$user_id/evaluations/biography_comparisons.csv"
        bio_comparisons=$(count_csv_rows "$bio_csv")
    fi
    
    # For interview comparisons, check session-specific rows
    interview_csv="logs/$user_id/evaluations/interview_comparisons.csv"
    if [ -n "$SESSION_ID" ]; then
        interview_comparisons=$(count_session_comparisons "$interview_csv" "$SESSION_ID")
    else
        interview_comparisons=$(count_csv_rows "$interview_csv")
    fi
    
    echo "Found $bio_comparisons biography comparisons"
    echo "Found $interview_comparisons interview comparisons"
    
    # Calculate how many more runs needed for each type
    bio_needed=0
    if [[ "$COMPARISON_TYPE" == "all" || "$COMPARISON_TYPE" == "bio" ]]; then
        if [ $bio_comparisons -lt $TOTAL_NEEDED ]; then
            bio_needed=$((TOTAL_NEEDED - bio_comparisons))
            echo "Need $bio_needed more biography evaluations to reach target of $TOTAL_NEEDED"
        else
            echo "Already have enough biography comparisons (target: $TOTAL_NEEDED)"
        fi
    else
        echo "Skipping biography comparisons as per --type parameter"
    fi
    
    interview_needed=0
    if [[ "$COMPARISON_TYPE" == "all" || "$COMPARISON_TYPE" == "interview" ]]; then
        if [ $interview_comparisons -lt $TOTAL_NEEDED ]; then
            interview_needed=$((TOTAL_NEEDED - interview_comparisons))
            echo "Need $interview_needed more interview evaluations to reach target of $TOTAL_NEEDED"
        else
            echo "Already have enough interview comparisons (target: $TOTAL_NEEDED)"
        fi
    else
        echo "Skipping interview comparisons as per --type parameter"
    fi
    
    # Run biography evaluations if needed
    if [ $bio_needed -gt 0 ]; then
        echo "Running biography evaluations..."
        for ((i=1; i<=$bio_needed; i++)); do
            echo "Biography run $i of $bio_needed..."
            if [ -n "$SESSION_ID" ]; then
                python evaluations/biography_content.py --user_id "$user_id" --biography_version "$SESSION_ID"
            else
                python evaluations/biography_content.py --user_id "$user_id"
            fi
            echo "Completed biography run $i"
        done
    fi
    
    # Run interview evaluations if needed
    if [ $interview_needed -gt 0 ]; then
        echo "Running interview evaluations..."
        for ((i=1; i<=$interview_needed; i++)); do
            echo "Interview run $i of $interview_needed..."
            if [ -n "$SESSION_ID" ]; then
                python evaluations/interview_content.py --user_id "$user_id" --session_id "$SESSION_ID"
            else
                python evaluations/interview_content.py --user_id "$user_id"
            fi
            echo "Completed interview run $i"
        done
    fi
    
    echo "Evaluations completed for user $user_id"
    echo "-------------------"
done

# Show final comparison results
echo "Showing final comparison results..."
COMMAND="python ${SCRIPT_DIR}/analysis/comparison_results.py --user_ids ${USER_IDS[@]}"
if [ -n "$SESSION_ID" ]; then
    COMMAND="$COMMAND --biography_version $SESSION_ID --session_id $SESSION_ID"
fi
echo "Running command: $COMMAND"
eval "$COMMAND" 