#!/usr/bin/env python3
import os
import csv
import argparse
from typing import Dict, List, Optional
from collections import defaultdict
import pandas as pd
from pathlib import Path

def aggregate_single_file(df: pd.DataFrame, latency_df: Optional[pd.DataFrame] = None, bio_update_df: Optional[pd.DataFrame] = None) -> Dict:
    """Aggregate statistics from a single CSV file.
    
    Args:
        df: DataFrame containing conversation statistics
        latency_df: Optional DataFrame containing response latency data
        bio_update_df: Optional DataFrame containing biography update times
        
    Returns:
        Dictionary with aggregated statistics
    """
    stats = {
        'Sessions': len(df),
        'Total Turns': df['Total Turns'].sum(),
        'Total Memories': df['Total Memories'].sum(),
        'Tokens per Conv': df['Total Tokens'].mean()
    }
    
    # Add latency and message length statistics if available
    if latency_df is not None and not latency_df.empty:
        stats['Avg Latency'] = latency_df['Latency (seconds)'].mean()
        stats['Msg Length'] = latency_df['User Message Length'].mean()
    else:
        stats['Avg Latency'] = 0
        stats['Msg Length'] = 0
    
    # Add biography update time statistics if available
    if bio_update_df is not None and not bio_update_df.empty:
        # Filter for final updates only
        final_updates = bio_update_df[bio_update_df['Update Type'] == 'final']
        stats['Bio Update Time'] = final_updates['Duration (seconds)'].mean()
    else:
        stats['Bio Update Time'] = 0
    
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
        bio_update_file = base_path / "biography_update_times.csv"
        
        if conv_file.exists():
            conv_df = pd.read_csv(conv_file)
            latency_df = pd.read_csv(latency_file) if \
                latency_file.exists() else None
            bio_update_df = pd.read_csv(bio_update_file) if \
                bio_update_file.exists() else None
            file_stats = aggregate_single_file(conv_df, latency_df, bio_update_df)
            file_stats['Model'] = 'Ours'
            stats.append(file_stats)
    
    # Then check model-specific directories (baselines)
    for dir_name in os.listdir('.'):
        if dir_name.startswith('logs_'):  # baseline experiments
            model_name = dir_name[5:]  # Remove 'logs_' prefix
            base_path = Path(dir_name) / user_id / "evaluations"
            if base_path.exists():
                conv_file = base_path / "conversation_statistics.csv"
                latency_file = base_path / "response_latency.csv"
                bio_update_file = base_path / "biography_update_times.csv"
                
                if conv_file.exists():
                    conv_df = pd.read_csv(conv_file)
                    latency_df = pd.read_csv(latency_file) \
                        if latency_file.exists() else None
                    bio_update_df = pd.read_csv(bio_update_file) \
                        if bio_update_file.exists() else None
                    file_stats = aggregate_single_file(conv_df, latency_df, bio_update_df)
                    file_stats['Model'] = model_name
                    stats.append(file_stats)
    
    return stats

def aggregate_stats(stats: List[Dict]) -> Dict[str, Dict]:
    """Aggregate statistics by model.
    Average metrics across different files/users for each model.
    
    Args:
        stats: List of statistics dictionaries
        
    Returns:
        Dictionary mapping model names to their statistics
    """
    model_stats = defaultdict(list)
    
    for stat in stats:
        model = stat.pop('Model')  # Remove and get model name
        model_stats[model].append(stat)
    
    # Average metrics for each model
    averaged_stats = {}
    for model, model_data in model_stats.items():
        if model_data:
            # Initialize with first dict's keys
            summed = defaultdict(float)
            for data in model_data:
                for key, value in data.items():
                    summed[key] += value
            
            averaged_stats[model] = {
                key: value / len(model_data)
                for key, value in summed.items()
            }
    
    return averaged_stats

def display_results(stats_by_model: Dict[str, Dict]) -> None:
    """Display results in a formatted table.
    
    Args:
        stats_by_model: Dictionary mapping model names to their statistics
    """
    print("\nConversation Statistics:")
    print("-" * 80)  # Increased width for new column
    print(f"{'Model':<20} "
          f"{'Sessions':>8} {'Turns':>8} {'Memories':>10} "
        #   f"{'Tokens/Conv':>12} "
          f"{'Latency(s)':>12} "
        #   f"{'User Msg Len':>14} "
          f"{'Bio Update(s)':>12}")
    print("-" * 80)  # Increased width for new column
    
    # Sort models to ensure 'Ours' is last
    models = sorted([m for m in stats_by_model.keys() if m != 'Ours']) + \
             (['Ours'] if 'Ours' in stats_by_model else [])
    
    for model in models:
        stats = stats_by_model[model]
        print(f"{model:<20} {int(stats['Sessions']):>8} "
              f"{int(stats['Total Turns'] / 2):>8} "
              f"{int(stats['Total Memories']):>10} "
            #   f"{int(stats['Tokens per Conv']):>12} "
              f"{stats['Avg Latency']:>12.2f} "
            #   f"{int(stats['Msg Length']):>12} "
              f"{stats['Bio Update Time']:>12.2f}")
    
    print("-" * 80)  # Increased width for new column

def analyze_user_stats(user_id: str) -> Dict[str, Dict]:
    """Analyze conversation statistics for a single user.
    
    Args:
        user_id: The user ID to analyze
        
    Returns:
        Dictionary mapping model names to their statistics
    """
    stats = load_conversation_stats(user_id)
    return aggregate_stats(stats)

def analyze_multiple_users(user_ids: List[str]) -> Dict[str, Dict]:
    """Analyze conversation statistics for multiple users.
    
    Args:
        user_ids: List of user IDs to analyze
        
    Returns:
        Dictionary mapping model names to their statistics
    """
    all_stats = []
    for user_id in user_ids:
        stats = load_conversation_stats(user_id)
        all_stats.extend(stats)
    
    return aggregate_stats(all_stats)

def main():
    parser = argparse.ArgumentParser(description="Analyze conversation statistics")
    parser.add_argument('--user_ids', nargs='+', required=True,
                      help='One or more user IDs to analyze')
    args = parser.parse_args()
    
    if len(args.user_ids) == 1:
        stats_by_model = analyze_user_stats(args.user_ids[0])
    else:
        stats_by_model = analyze_multiple_users(args.user_ids)
    
    display_results(stats_by_model)

if __name__ == '__main__':
    main() 