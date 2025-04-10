#!/usr/bin/env python3
"""
Biography Statistics Report Generator

This script loads the newest biography version for each user in a provided list
and appends their statistics to a single bio_stats.csv file in the logs_bio directory.

Usage:
    python generate_bio_reports.py --users user1 user2 user3
    python generate_bio_reports.py --file users.txt

Where users.txt contains one user ID per line.
"""

import os
import sys
import asyncio
import argparse
from typing import List

# Add the src directory to the Python path to import from the project
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))

# Import the Biography class
from content.biography.biography import Biography


async def process_user(user_id: str) -> bool:
    """
    Load the latest biography for a user and generate a statistics report.
    
    Args:
        user_id: The ID of the user to process
        
    Returns:
        True if the biography was found and processed, False otherwise
    """
    print(f"Processing user: {user_id}")
    
    # Load the latest biography for the user
    biography = Biography.load_from_file(user_id)
    
    # Check if biography exists (has content)
    if biography.version < 1:
        print(f"  No biography found for user {user_id}")
        return False
    
    print(f"  Loaded biography version {biography.version}")
    
    # Generate stats report and append to the CSV file
    await biography.generate_stats_report(save_to_file=True)
    return True


def read_users_from_file(file_path: str) -> List[str]:
    """
    Read a list of user IDs from a text file.
    
    Args:
        file_path: Path to a text file with one user ID per line
        
    Returns:
        List of user IDs
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]


async def main():
    parser = argparse.ArgumentParser(description='Generate biography statistics reports for multiple users.')
    
    # Define mutually exclusive group for user IDs
    user_group = parser.add_mutually_exclusive_group(required=True)
    user_group.add_argument('--users', '-u', nargs='+', help='List of user IDs to process')
    user_group.add_argument('--file', '-f', help='Path to file containing user IDs (one per line)')
    
    args = parser.parse_args()
    
    # Get user IDs either from command line or from file
    if args.file:
        users = read_users_from_file(args.file)
        print(f"Loaded {len(users)} user IDs from {args.file}")
    else:
        users = args.users
    
    if not users:
        parser.error("No user IDs provided.")
    
    # Process each user
    processed_count = 0
    for user_id in users:
        if await process_user(user_id):
            processed_count += 1
    
    print(f"\nProcessed {processed_count} out of {len(users)} users.")
    print(f"All statistics have been appended to logs_bio/bio_stats.csv")


if __name__ == "__main__":
    asyncio.run(main()) 