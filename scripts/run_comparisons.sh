#!/bin/bash

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Default values
RUN_TIMES=10
BIO_VERSION=""
COMPARISON_TYPE="all"  # Default to running both types

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --run_times)
            RUN_TIMES="$2"
            shift 2
            ;;
        --bio_version)
            BIO_VERSION="$2"
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
    echo "Usage: ./scripts/run_comparisons.sh [--run_times N] [--bio_version V] [--type all|bio|interview] <user_id1> [user_id2 ...]"
    exit 1
fi

# Validate comparison type
if [[ "$COMPARISON_TYPE" != "all" && "$COMPARISON_TYPE" != "bio" && "$COMPARISON_TYPE" != "interview" ]]; then
    echo "Error: Invalid comparison type. Must be 'all', 'bio', or 'interview'"
    echo "Usage: ./scripts/run_comparisons.sh [--run_times N] [--bio_version V] [--type all|bio|interview] <user_id1> [user_id2 ...]"
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

# Run evaluations multiple times for each user
for user_id in "${USER_IDS[@]}"; do
    echo "Running evaluations for user: $user_id"
    
    # Find biography directory based on version parameter or latest
    if [ -n "$BIO_VERSION" ]; then
        bio_dir="logs/$user_id/evaluations/biography_$BIO_VERSION"
        echo "Using specified biography version: $BIO_VERSION"
    else
        bio_dir=$(ls -d logs/"$user_id"/evaluations/biography_* 2>/dev/null | sort -V | tail -n 1)
        if [ -n "$bio_dir" ]; then
            BIO_VERSION=$(basename "$bio_dir" | cut -d'_' -f2)
            echo "Using latest biography version: $BIO_VERSION"
        else
            echo "No biography versions found for user $user_id"
            BIO_VERSION=""
        fi
    fi
    
    # Check existing comparison counts
    bio_comparisons=0
    interview_comparisons=0
    
    if [ -n "$bio_dir" ] && [ -d "$bio_dir" ]; then
        bio_csv="$bio_dir/biography_comparisons.csv"
        bio_comparisons=$(count_csv_rows "$bio_csv")
    fi
    
    interview_csv="logs/$user_id/evaluations/interview_comparisons.csv"
    interview_comparisons=$(count_csv_rows "$interview_csv")
    
    echo "Found $bio_comparisons biography comparisons"
    echo "Found $interview_comparisons interview comparisons"
    
    # Calculate how many more biography runs needed
    bio_needed=0
    if [[ "$COMPARISON_TYPE" == "all" || "$COMPARISON_TYPE" == "bio" ]]; then
        if [ $bio_comparisons -lt $RUN_TIMES ]; then
            bio_needed=$((RUN_TIMES - bio_comparisons))
            echo "Need $bio_needed more biography evaluations to reach target of $RUN_TIMES"
        else
            echo "Already have enough biography comparisons (target: $RUN_TIMES)"
        fi
    else
        echo "Skipping biography comparisons as per --type parameter"
    fi
    
    # Calculate how many more interview runs needed
    interview_needed=0
    if [[ "$COMPARISON_TYPE" == "all" || "$COMPARISON_TYPE" == "interview" ]]; then
        if [ $interview_comparisons -lt $RUN_TIMES ]; then
            interview_needed=$((RUN_TIMES - interview_comparisons))
            echo "Need $interview_needed more interview evaluations to reach target of $RUN_TIMES"
        else
            echo "Already have enough interview comparisons (target: $RUN_TIMES)"
        fi
    else
        echo "Skipping interview comparisons as per --type parameter"
    fi
    
    # Run biography evaluations if needed
    if [ $bio_needed -gt 0 ]; then
        echo "Running biography evaluations..."
        for ((i=1; i<=$bio_needed; i++)); do
            echo "Biography run $i of $bio_needed..."
            if [ -n "$BIO_VERSION" ]; then
                python evaluations/biography_content.py --user_id "$user_id" --biography_version "$BIO_VERSION"
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
            python evaluations/interview_content.py --user_id "$user_id"
            echo "Completed interview run $i"
        done
    fi
    
    echo "Evaluations completed for user $user_id"
    echo "-------------------"
done

# Build the command to show comparison results
COMMAND="python ${SCRIPT_DIR}/analysis/comparison_results.py --user_ids ${USER_IDS[@]}"
if [ -n "$BIO_VERSION" ]; then
    COMMAND="$COMMAND --biography_version $BIO_VERSION"
fi

# Print the command
echo "Showing final comparison results..."
echo "Running command: $COMMAND"

# Run the command
eval "$COMMAND" 