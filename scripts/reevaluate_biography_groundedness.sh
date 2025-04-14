#!/bin/bash

# Script to re-evaluate biography groundedness for multiple users across sessions 1-10
# Usage: ./reevaluate_biography_groundedness.sh user1 user2 user3 ...

# Check if at least one user ID is provided
if [ $# -eq 0 ]; then
    echo "Error: No user IDs provided."
    echo "Usage: ./reevaluate_biography_groundedness.sh user1 user2 user3 ..."
    exit 1
fi

# Activate virtual environment if needed (uncomment and adjust if necessary)
# source venv/bin/activate

# Set MAX_CONSIDERATION_ITERATIONS environment variable to ensure proper retries
export MAX_CONSIDERATION_ITERATIONS=3

# Process each user ID
for user_id in "$@"; do
    echo "=========================================="
    echo "Processing user: $user_id"
    echo "=========================================="
    
    # Process each session from 1 to 10
    for session in {1..10}; do
        echo "Evaluating biography groundedness for $user_id, session $session"
        
        # Run groundedness evaluation for this user and session
        python evaluations/biography_groundedness.py --user_id "$user_id" --version "$session"
        
        # Check the exit status
        if [ $? -eq 0 ]; then
            echo "✅ Successfully evaluated groundedness for $user_id, session $session"
        else
            echo "❌ Failed to evaluate groundedness for $user_id, session $session"
        fi
    done
    
    echo "Completed processing for user: $user_id"
    echo ""
done

echo "All users processed. Evaluation complete."
