#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
from statistics import mode, multimode

def read_users(users_file):
    """Read the list of users from users.txt"""
    with open(users_file, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def format_number(x):
    """Format number to 2 decimal places if float, or as is if integer"""
    if isinstance(x, float):
        return f"{x:.2f}"
    return str(x)

def get_mode(data):
    """Get mode(s) of the data, handling both single and multiple modes"""
    try:
        modes = multimode(data)
        return ', '.join(format_number(m) for m in modes)
    except:
        return "N/A"

def get_min_max_info(data, user_ids):
    """Get minimum and maximum values with their corresponding user IDs"""
    min_idx = data.idxmin()
    max_idx = data.idxmax()
    return {
        'min_value': data.min(),
        'min_user': user_ids[min_idx],
        'max_value': data.max(),
        'max_user': user_ids[max_idx]
    }

def format_table_row(user_id, sessions_data):
    """Format a single row of the user sessions table"""
    num_sessions = len(sessions_data)
    rounds_str = " + ".join(str(int(turns/2)) for turns in sessions_data['Total Turns'])
    return f"| {user_id:<15} | {num_sessions:^14} | {rounds_str:<50} |"

def analyze_conversations():
    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent
    users_file = project_root / 'logs_bio' / 'users.txt'
    
    # Read users list
    users = read_users(users_file)
    
    # Initialize variables for aggregation
    all_stats = []
    user_sessions = {}
    
    # Process each user's conversation statistics
    for user in users:
        stats_file = project_root / 'logs_server' / user / 'evaluations' / 'conversation_statistics.csv'
        if stats_file.exists():
            try:
                df = pd.read_csv(stats_file)
                df['user_id'] = user  # Add user_id column
                all_stats.append(df)
                user_sessions[user] = df
            except Exception as e:
                print(f"Error processing {user}: {e}")
    
    if not all_stats:
        print("No conversation statistics found!")
        return
    
    # Print user sessions table
    print("\nUser Session Statistics")
    print("=" * 85)
    header = "| User ID         | Total Sessions | Rounds per Session                                       |"
    print(header)
    print("|" + "-" * 16 + "|" + "-" * 15 + "|" + "-" * 51 + "|")
    
    # Sort users by ID for consistent output
    for user in sorted(user_sessions.keys()):
        print(format_table_row(user, user_sessions[user]))
    
    print("=" * 85)
    
    # Calculate detailed statistics
    combined_stats = pd.concat(all_stats, ignore_index=True)
    rounds_per_session = combined_stats['Total Turns'] / 2
    min_max = get_min_max_info(rounds_per_session, combined_stats['user_id'])
    
    print("\nRounds per Session Statistics:")
    print("-" * 50)
    print(f"Mean:           {rounds_per_session.mean():.2f}")
    print(f"Median:         {rounds_per_session.median():.2f}")
    print(f"25th Percentile: {rounds_per_session.quantile(0.25):.2f}")
    print(f"75th Percentile: {rounds_per_session.quantile(0.75):.2f}")
    print(f"Minimum:        {min_max['min_value']:.2f} (User: {min_max['min_user']})")
    print(f"Maximum:        {min_max['max_value']:.2f} (User: {min_max['max_user']})")
    print(f"Std Deviation:  {rounds_per_session.std():.2f}")
    
    # Print overall summary
    total_users = len(user_sessions)
    total_sessions = len(combined_stats)
    total_rounds = rounds_per_session.sum()
    
    print(f"\nOverall Summary:")
    print("-" * 50)
    print(f"Total Users: {total_users}")
    print(f"Total Sessions: {total_sessions}")
    print(f"Total Rounds: {int(total_rounds)}")
    print(f"Average Sessions per User: {total_sessions/total_users:.2f}")
    print(f"Average Rounds per Session: {total_rounds/total_sessions:.2f}")

if __name__ == "__main__":
    analyze_conversations() 