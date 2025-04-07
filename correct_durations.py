import os
import csv
from datetime import datetime
import re
from typing import Optional, Tuple

def parse_timestamp_from_log_line(line: str) -> Optional[datetime]:
    """Extract timestamp from a log line."""
    # Example: 2025-03-29 15:51:18,983 [MEMORY] Collected...
    match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})', line)
    if match:
        timestamp_str = match.group(1)
        return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
    return None

def find_update_timestamps(log_file_path: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Find the timestamps for memory collection and biography update."""
    memory_collection_time = None
    biography_update_time = None
    
    with open(log_file_path, 'r') as f:
        lines = f.readlines()
        
        # Read lines in reverse to find the last unprocessed memory collection
        for line in reversed(lines):
            if '[MEMORY] Collected' in line and 'unprocessed memories' in line:
                memory_collection_time = parse_timestamp_from_log_line(line)
                break
        
        # Find the last biography update completion in the file
        for line in reversed(lines):
            if '[BIOGRAPHY] Executed' in line:
                biography_update_time = parse_timestamp_from_log_line(line)
                break
    
    return memory_collection_time, biography_update_time

def correct_durations(logs_dir: str, user_id: str):
    """Correct duration calculations for a user's biography updates."""
    csv_path = os.path.join(logs_dir, user_id, 'evaluations', 'biography_update_times.csv')
    if not os.path.exists(csv_path):
        print(f"No biography update times file found for user {user_id}")
        return
        
    # Read existing data
    rows = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Process each session
    for row in rows:
        session_num = row['Session ID']
        log_file = os.path.join(logs_dir, user_id, 'execution_logs',
                                 f'session_{session_num}', 'execution_log.log')
        
        if os.path.exists(log_file):
            memory_time, update_time = find_update_timestamps(log_file)
            if memory_time and update_time:
                duration = (update_time - memory_time).total_seconds()
                # If there's an underscore in logs_dir, add Accumulated Auto Time
                if '_' in os.path.basename(logs_dir):
                    try:
                        auto_time = float(row.get('Accumulated Auto Time', 0))
                        duration += auto_time
                    except (ValueError, TypeError):
                        pass
                row['Correct Duration'] = f"{duration:.2f}"
            else:
                row['Correct Duration'] = "N/A"
        else:
            row['Correct Duration'] = "N/A"
    
    # Write corrected data back
    fieldnames = list(rows[0].keys())
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        
def main(logs_dir: str = "logs"):
    """Process all users in the logs directory."""
    for user_id in os.listdir(logs_dir):
        user_dir = os.path.join(logs_dir, user_id)
        if os.path.isdir(user_dir):
            print(f"Processing user {user_id}...")
            correct_durations(logs_dir, user_id)
            print(f"Completed processing user {user_id}")

if __name__ == "__main__":
    import sys
    logs_dir = sys.argv[1] if len(sys.argv) > 1 else "logs"
    main(logs_dir) 