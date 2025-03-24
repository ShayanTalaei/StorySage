#!/usr/bin/env python3
import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List
import re

def get_model_name(directory: str) -> str:
    """Extract model name from directory.
    
    Args:
        directory: Directory name (e.g., 'logs' or 'logs_gpt4')
        
    Returns:
        Model name (e.g., 'ours' or 'gpt4')
    """
    if directory == 'logs':
        return 'ours'
    match = re.match(r'logs_(.+)', directory)
    return match.group(1) if match else directory

def plot_session_latencies(latency_data: Dict[str, pd.DataFrame], user_id: str):
    """Plot latency trends for each conversation session separately, comparing different models.
    
    Args:
        latency_data: Dictionary mapping model names to their DataFrame containing latency data
        user_id: ID of the user being analyzed
    """
    if not latency_data:
        print("No latency data available to plot")
        return
    
    # Create plots directory if it doesn't exist
    output_dir = Path('plots') / user_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all unique session IDs across all models
    all_sessions = set()
    for df in latency_data.values():
        all_sessions.update(df['Session ID'].unique())
    
    # Colors for different models
    colors = ['#2E86C1', '#E74C3C', '#27AE60', '#8E44AD', '#F39C12', '#16A085']
    
    # Plot each session separately
    for session_id in sorted(all_sessions):
        # Create a new figure for this session
        plt.figure(figsize=(12, 6))
        
        # Plot each model's data
        for (model_name, df), color in zip(latency_data.items(), colors):
            session_data = df[df['Session ID'] == session_id]
            if session_data.empty:
                continue
                
            # Sort by timestamp to get correct turn order
            session_data = session_data.sort_values('Timestamp')
            
            # Create turn numbers starting from 1
            turns = range(1, len(session_data) + 1)
            latencies = session_data['Latency (seconds)']
            
            # Calculate statistics
            mean_latency = latencies.mean()
            median_latency = latencies.median()
            std_latency = latencies.std()
            
            # Plot latency trend
            plt.plot(turns, latencies, marker='o', linestyle='-', color=color,
                    label=f'{model_name} (mean: {mean_latency:.2f}s)', 
                    linewidth=2, markersize=6)
            
            # Add mean line
            plt.axhline(y=mean_latency, color=color, linestyle='--', alpha=0.3)
            
            # Print model statistics
            print(f"\nSession {session_id} - {model_name} Statistics:")
            print(f"Number of turns: {len(turns)}")
            print(f"Mean latency: {mean_latency:.2f}s")
            print(f"Median latency: {median_latency:.2f}s")
            print(f"Standard deviation: {std_latency:.2f}s")
            print(f"Max latency: {latencies.max():.2f}s")
            print(f"Min latency: {latencies.min():.2f}s")
            
            # Annotate significant spikes
            threshold = mean_latency + 2 * std_latency
            for turn, latency in zip(turns, latencies):
                if latency > threshold:
                    plt.annotate(f'{latency:.2f}s', 
                               (turn, latency),
                               textcoords="offset points",
                               xytext=(0,10),
                               ha='center',
                               fontsize=9,
                               color=color)
        
        # Customize the plot
        plt.xlabel('Turn Number', fontsize=12)
        plt.ylabel('Latency (seconds)', fontsize=12)
        plt.title(f'Response Latency Comparison - Session {session_id}',
                 fontsize=14, pad=15)
        
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(fontsize=10, loc='upper left', bbox_to_anchor=(1, 1))
        
        # Add some padding to y-axis and adjust layout for legend
        plt.margins(y=0.1)
        plt.tight_layout()
        
        # Save the plot
        plot_path = output_dir / f'latency_comparison_session_{session_id}.png'
        plt.savefig(plot_path, bbox_inches='tight', dpi=300)
        print(f"Plot saved: {plot_path}")
        
        plt.close()

def load_latency_data(user_id: str) -> Dict[str, pd.DataFrame]:
    """Load latency data for a user from all relevant directories.
    
    Args:
        user_id: The user ID to analyze
        
    Returns:
        Dictionary mapping model names to their DataFrame containing latency data
    """
    model_data = {}
    
    # Check main logs directory (our model)
    base_path = Path('logs') / user_id / "evaluations"
    if base_path.exists():
        latency_file = base_path / "response_latency.csv"
        if latency_file.exists():
            df = pd.read_csv(latency_file)
            model_data['ours'] = df
    
    # Check baseline directories
    for dir_name in os.listdir('.'):
        if dir_name.startswith('logs_'):
            base_path = Path(dir_name) / user_id / "evaluations"
            if base_path.exists():
                latency_file = base_path / "response_latency.csv"
                if latency_file.exists():
                    model_name = get_model_name(dir_name)
                    df = pd.read_csv(latency_file)
                    model_data[model_name] = df
    
    return model_data

def main():
    parser = argparse.ArgumentParser(description="Analyze and visualize conversation latency")
    parser.add_argument('--user_ids', nargs='+', required=True,
                      help='One or more user IDs to analyze')
    args = parser.parse_args()
    
    for user_id in args.user_ids:
        print(f"\nAnalyzing latency data for user: {user_id}")
        model_data = load_latency_data(user_id)
        
        if not model_data:
            print(f"No latency data found for user {user_id}")
            continue
            
        plot_session_latencies(model_data, user_id)
        print(f"\nAll plots have been saved in: plots/{user_id}/")

if __name__ == '__main__':
    main() 