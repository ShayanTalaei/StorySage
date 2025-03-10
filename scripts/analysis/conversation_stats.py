#!/usr/bin/env python3
import os
import csv
import argparse
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import pandas as pd
from pathlib import Path

def aggregate_single_file(df: pd.DataFrame, latency_df: Optional[pd.DataFrame] = None) -> Dict:
    """Aggregate statistics from a single CSV file.
    
    Args:
        df: DataFrame containing conversation statistics
        latency_df: Optional DataFrame containing response latency data
        
    Returns:
        Dictionary with aggregated statistics
    """
    stats = {
        'Sessions': len(df),
        'Total Turns': df['Total Turns'].sum(),
        'Total Memories': df['Total Memories'].sum(),
        'Chars per Conv': df['Total Characters'].mean()
    }
    
    # Add latency and message length statistics if available
    if latency_df is not None and not latency_df.empty:
        stats['Avg Latency'] = latency_df['Latency (seconds)'].mean()
        stats['Msg Length'] = latency_df['User Message Length'].mean()
    else:
        stats['Avg Latency'] = 0
        stats['Msg Length'] = 0
    
    return stats

def load_conversation_stats(user_id: str) -> List[Dict]:
    """Load conversation statistics for a user from all relevant directories.
    
    Args:
        user_id: The user ID to analyze
        
    Returns:
        List of dictionaries containing conversation statistics
    """
    stats = []
    
    # First check main logs directory (our work)
    base_path = Path('logs') / user_id / "evaluations"
    if base_path.exists():
        conv_file = base_path / "conversation_statistics.csv"
        latency_file = base_path / "response_latency.csv"
        
        if conv_file.exists():
            conv_df = pd.read_csv(conv_file)
            latency_df = pd.read_csv(latency_file) if latency_file.exists() else None
            file_stats = aggregate_single_file(conv_df, latency_df)
            file_stats['Is Baseline'] = False  # our work
            stats.append(file_stats)
    
    # Then check model-specific directories (baselines)
    for dir_name in os.listdir('.'):
        if dir_name.startswith('logs_'):  # baseline experiments
            base_path = Path(dir_name) / user_id / "evaluations"
            if base_path.exists():
                conv_file = base_path / "conversation_statistics.csv"
                latency_file = base_path / "response_latency.csv"
                
                if conv_file.exists():
                    conv_df = pd.read_csv(conv_file)
                    latency_df = pd.read_csv(latency_file) \
                        if latency_file.exists() else None
                    file_stats = aggregate_single_file(conv_df, latency_df)
                    file_stats['Is Baseline'] = True  # baseline work
                    stats.append(file_stats)
    
    return stats

def aggregate_stats(stats: List[Dict]) -> Tuple[Dict, Dict]:
    """Aggregate statistics into baseline and non-baseline groups.
    Average all metrics across different files/users.
    
    Args:
        stats: List of statistics dictionaries
        
    Returns:
        Tuple of (baseline_stats, our_stats)
    """
    baseline_stats = defaultdict(list)
    our_stats = defaultdict(list)
    
    for stat in stats:
        target = baseline_stats if stat['Is Baseline'] else our_stats
        for key, value in stat.items():
            if key != 'Is Baseline':
                target[key].append(value)
    
    # Average all metrics for baseline stats
    if baseline_stats:
        baseline_avg = {
            key: sum(values) / len(values) 
            for key, values in baseline_stats.items()
        }
    else:
        baseline_avg = {
            'Sessions': 0, 'Total Turns': 0, 
            'Total Memories': 0, 'Chars per Conv': 0, 'Avg Latency': 0, 'Msg Length': 0
        }
    
    # Average all metrics for our stats
    if our_stats:
        our_avg = {
            key: sum(values) / len(values)
            for key, values in our_stats.items()
        }
    else:
        our_avg = {
            'Sessions': 0, 'Total Turns': 0, 
            'Total Memories': 0, 'Chars per Conv': 0, 'Avg Latency': 0, 'Msg Length': 0
        }
    
    return baseline_avg, our_avg

def analyze_user_stats(user_id: str) -> Tuple[Dict, Dict]:
    """Analyze conversation statistics for a single user.
    
    Args:
        user_id: The user ID to analyze
        
    Returns:
        Tuple of (baseline_stats, our_stats)
    """
    stats = load_conversation_stats(user_id)
    return aggregate_stats(stats)

def analyze_multiple_users(user_ids: List[str]) -> Tuple[Dict, Dict]:
    """Analyze conversation statistics for multiple users.
    
    Args:
        user_ids: List of user IDs to analyze
        
    Returns:
        Tuple of (baseline_stats, our_stats)
    """
    all_stats = []
    for user_id in user_ids:
        stats = load_conversation_stats(user_id)
        all_stats.extend(stats)
    
    return aggregate_stats(all_stats)

def display_results(baseline_stats: Dict, our_stats: Dict) -> None:
    """Display results in a formatted table.
    
    Args:
        baseline_stats: Aggregated baseline statistics
        our_stats: Aggregated statistics for our method
    """
    print("\nConversation Statistics:")
    print("-" * 110)
    print(f"{'Model':<20} {'Sessions':>8} {'Turns':>8} {'Memories':>10} {'Chars/Conv':>12} {'Latency(s)':>12} {'User Msg Len':>14}")
    print("-" * 110)
    
    # Format baseline stats
    print(f"(Avg.) baselines{' ':>4} {int(baseline_stats['Sessions']):>8} "
          f"{int(baseline_stats['Total Turns']):>8} "
          f"{int(baseline_stats['Total Memories']):>10} "
          f"{int(baseline_stats['Chars per Conv']):>12} "
          f"{baseline_stats['Avg Latency']:>12.2f} "
          f"{int(baseline_stats['Msg Length']):>12}")
    
    # Format our stats
    print(f"Ours{' ':>16} {int(our_stats['Sessions']):>8} "
          f"{int(our_stats['Total Turns']):>8} "
          f"{int(our_stats['Total Memories']):>10} "
          f"{int(our_stats['Chars per Conv']):>12} "
          f"{our_stats['Avg Latency']:>12.2f} "
          f"{int(our_stats['Msg Length']):>12}")
    print("-" * 110)

def main():
    parser = argparse.ArgumentParser(description="Analyze conversation statistics")
    parser.add_argument('--user_ids', nargs='+', required=True,
                      help='One or more user IDs to analyze')
    args = parser.parse_args()
    
    if len(args.user_ids) == 1:
        baseline_stats, our_stats = analyze_user_stats(args.user_ids[0])
    else:
        baseline_stats, our_stats = analyze_multiple_users(args.user_ids)
    
    display_results(baseline_stats, our_stats)

if __name__ == '__main__':
    main() 