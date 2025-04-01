#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import re
from typing import Dict

def get_session_metrics(eval_dir: Path) -> Dict[int, Dict[str, float]]:
    """Get biography metrics for each session in chronological order.
    
    Args:
        eval_dir: Path to the evaluations directory
        
    Returns:
        Dictionary mapping session numbers to their metrics
    """
    session_metrics = {}
    
    # Get all biography version directories
    bio_dirs = [d for d in eval_dir.glob("biography_*") if d.is_dir()]
    if not bio_dirs:
        return session_metrics
    
    for bio_dir in bio_dirs:
        # Extract session number from directory name
        match = re.search(r'biography_(\d+)', str(bio_dir))
        if not match:
            continue
            
        session_num = int(match.group(1))
        metrics = {}
        
        # Load completeness
        completeness_file = bio_dir / "completeness_summary.csv"
        if completeness_file.exists():
            df = pd.read_csv(completeness_file, nrows=4)
            coverage = df.loc[df['Metric'] == 'Memory Coverage', 'Value'].iloc[0]
            total_memories = df.loc[df['Metric'] == 'Total Memories', 'Value'].iloc[0]
            referenced_memories = df.loc[df['Metric'] == 'Referenced Memories', 
                                         'Value'].iloc[0]
            
            metrics['completeness'] = float(coverage.strip('%'))
            metrics['total_memories'] = int(total_memories)
            metrics['referenced_memories'] = int(referenced_memories)
        
        # Load groundedness
        groundedness_file = bio_dir / "overall_groundedness.csv"
        if groundedness_file.exists():
            df = pd.read_csv(groundedness_file, nrows=1)
            groundedness = df['Overall Groundedness Score'].iloc[0]
            metrics['groundedness'] = float(groundedness.strip('%'))
        
        if metrics:
            session_metrics[session_num] = metrics
    
    return session_metrics

def plot_metrics_progression(metrics_data: Dict[str, Dict[int, Dict[str, float]]], user_id: str):
    """Plot how biography metrics change across sessions.
    
    Args:
        metrics_data: Dictionary mapping model names to their session metrics
        user_id: ID of the user being analyzed
    """
    if not metrics_data:
        print("No metrics data available to plot")
        return
    
    # Create plots directory if it doesn't exist
    output_dir = Path('plots') / user_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Colors for different models
    colors = ['#2E86C1', '#E74C3C', '#27AE60', '#8E44AD', '#F39C12', '#16A085']
    
    # Create separate plots for completeness and groundedness
    metrics_to_plot = ['completeness', 'groundedness']
    titles = ['Memory Coverage Progression', 'Groundedness Score Progression']
    y_labels = ['Memory Coverage (%)', 'Groundedness Score (%)']
    
    for metric, title, y_label in zip(metrics_to_plot, titles, y_labels):
        plt.figure(figsize=(12, 6))
        
        # Plot each model's progression
        for (model_name, sessions), color in zip(metrics_data.items(), colors):
            if not sessions:
                continue
            
            # Get all session numbers and values, sorted by session number
            session_nums = sorted(sessions.keys())
            values = [sessions[num][metric] for num in session_nums if metric in sessions[num]]
            
            if not values:
                continue
            
            # Plot progression
            plt.plot(session_nums, values, marker='o', linestyle='-', color=color,
                    label=f'{model_name}', linewidth=2, markersize=6)
            
            # Annotate final value
            plt.annotate(f'{values[-1]:.1f}%', 
                       (session_nums[-1], values[-1]),
                       textcoords="offset points",
                       xytext=(5, 5),
                       ha='left',
                       fontsize=9,
                       color=color)
        
        # Customize the plot
        plt.xlabel('Session Number', fontsize=12)
        plt.ylabel(y_label, fontsize=12)
        plt.title(title, fontsize=14, pad=15)
        
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(fontsize=10, loc='upper left', bbox_to_anchor=(1, 1))
        
        # Set y-axis range based on metric
        all_values = [val for model_data in metrics_data.values() 
                     for session in model_data.values() 
                     if metric in session
                     for val in [session[metric]]]
        
        # Calculate dynamic min_y with 30% padding (but not below 0)
        min_val = min(all_values) if all_values else 0
        padding = 30  # 30% padding
        min_y = max(min_val - padding, 0)
        plt.ylim(min_y, 100)
        
        # Set appropriate tick spacing based on the y-axis range
        tick_spacing = 5 if (100 - min_y) <= 50 else 10
        plt.yticks(range(int(min_y), 101, tick_spacing))
        
        # Set x-axis to show all session numbers
        all_sessions = {num for model_data in metrics_data.values() 
                       for num in model_data.keys()}
        plt.xlim(min(all_sessions) - 0.5, max(all_sessions) + 0.5)
        plt.xticks(sorted(all_sessions))
        
        # Add some padding and adjust layout
        plt.margins(x=0.1)
        plt.tight_layout()
        
        # Save the plot
        metric_name = metric.lower()
        plot_path = output_dir / f'biography_{metric_name}_progression.png'
        plt.savefig(plot_path, bbox_inches='tight', dpi=300)
        print(f"Plot saved: {plot_path}")
        
        plt.close()

def plot_memory_counts_progression(metrics_data: Dict[str, Dict[int, Dict[str, float]]], user_id: str):
    """Plot how memory counts change across sessions for each model.
    
    Args:
        metrics_data: Dictionary mapping model names to their session metrics
        user_id: ID of the user being analyzed
    """
    if not metrics_data:
        print("No metrics data available to plot")
        return
    
    output_dir = Path('plots') / user_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create separate plot for each model
    for model_name, sessions in metrics_data.items():
        if not sessions:
            continue
            
        plt.figure(figsize=(10, 6))
        
        # Get all session numbers and values, sorted by session number
        session_nums = sorted(sessions.keys())
        total_memories = [sessions[num]['total_memories'] for num in session_nums 
                         if 'total_memories' in sessions[num]]
        referenced_memories = [sessions[num]['referenced_memories'] for num in session_nums 
                             if 'referenced_memories' in sessions[num]]
        
        if not total_memories or not referenced_memories:
            continue
        
        # Plot both lines
        plt.plot(session_nums, total_memories, marker='o', linestyle='-', color='#2E86C1',
                label='Total Memories', linewidth=2, markersize=6)
        plt.plot(session_nums, referenced_memories, marker='o', linestyle='-',
                  color='#E74C3C',
                label='Referenced Memories', linewidth=2, markersize=6)
        
        # Annotate final values
        plt.annotate(f'{total_memories[-1]}', 
                    (session_nums[-1], total_memories[-1]),
                    textcoords="offset points",
                    xytext=(5, 5),
                    ha='left',
                    fontsize=9,
                    color='#2E86C1')
        plt.annotate(f'{referenced_memories[-1]}', 
                    (session_nums[-1], referenced_memories[-1]),
                    textcoords="offset points",
                    xytext=(5, 5),
                    ha='left',
                    fontsize=9,
                    color='#E74C3C')
        
        # Customize the plot
        plt.xlabel('Session Number', fontsize=12)
        plt.ylabel('Number of Memories', fontsize=12)
        plt.title(f'Memory Counts Progression - {model_name}', fontsize=14, pad=15)
        
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(fontsize=10, loc='upper left')
        
        # Set y-axis range
        all_values = total_memories + referenced_memories
        min_y = max(min(all_values) - 2, 0)
        max_y = max(all_values) + 2
        plt.ylim(min_y, max_y)
        
        # Set x-axis to show all session numbers
        plt.xlim(min(session_nums) - 0.5, max(session_nums) + 0.5)
        plt.xticks(session_nums)
        
        # Add padding and adjust layout
        plt.margins(x=0.1)
        plt.tight_layout()
        
        # Save the plot
        plot_path = output_dir / f'biography_memory_counts_{model_name}.png'
        plt.savefig(plot_path, bbox_inches='tight', dpi=300)
        print(f"Plot saved: {plot_path}")
        
        plt.close()

def load_progression_data(user_id: str) -> Dict[str, Dict[int, Dict[str, float]]]:
    """Load biography progression data for all models.
    
    Args:
        user_id: The user ID to analyze
        
    Returns:
        Dictionary mapping model names to their session metrics
    """
    model_data = {}
    
    # Load our model's data
    base_path = Path('logs') / user_id / "evaluations"
    if base_path.exists():
        metrics = get_session_metrics(base_path)
        if metrics:
            model_data['ours'] = metrics
    
    # Load baseline models' data
    for dir_name in os.listdir('.'):
        if dir_name.startswith('logs_'):
            model_name = dir_name[5:]  # Remove 'logs_' prefix
            base_path = Path(dir_name) / user_id / "evaluations"
            if base_path.exists():
                metrics = get_session_metrics(base_path)
                if metrics:
                    model_data[model_name] = metrics
    
    return model_data

def plot_aggregated_metrics_progression(all_users_data: Dict[str, Dict[str, Dict[int, Dict[str, float]]]], 
                                      output_dir: Path):
    """Plot average biography metrics across all users.
    
    Args:
        all_users_data: Dictionary mapping user_ids to their model data
                       {user_id: {model_name: {session_id: metrics}}}
        output_dir: Directory to save the plot
    """
    if not all_users_data:
        print("No metrics data available to plot")
        return
    
    # Colors for different models
    colors = ['#2E86C1', '#E74C3C', '#27AE60', '#8E44AD', '#F39C12', '#16A085']
    
    # Get all model names from the first user's data
    first_user = next(iter(all_users_data.values()))
    model_names = list(first_user.keys())
    
    # Get all session numbers (should be same for all users)
    first_model = next(iter(first_user.values()))
    session_nums = sorted(first_model.keys())
    
    # Create separate plots for completeness and groundedness
    metrics_to_plot = ['completeness', 'groundedness']
    titles = ['Average Memory Coverage Progression Across Users', 
             'Average Groundedness Score Progression Across Users']
    y_labels = ['Memory Coverage (%)', 'Groundedness Score (%)']
    
    for metric, title, y_label in zip(metrics_to_plot, titles, y_labels):
        plt.figure(figsize=(12, 6))
        
        # Plot each model's progression
        for model_name, color in zip(model_names, colors):
            # Calculate average values across users for each session
            avg_values = []
            for session in session_nums:
                values = [user_data[model_name][session][metric] 
                         for user_data in all_users_data.values()
                         if metric in user_data[model_name][session]]
                if values:
                    avg_values.append(sum(values) / len(values))
            
            if not avg_values:
                continue
            
            # Plot progression
            plt.plot(session_nums[:len(avg_values)], avg_values, marker='o', 
                    linestyle='-', color=color,
                    label=f'{model_name}', linewidth=2, markersize=6)
            
            # Annotate final value
            plt.annotate(f'{avg_values[-1]:.1f}%', 
                       (session_nums[len(avg_values)-1], avg_values[-1]),
                       textcoords="offset points",
                       xytext=(5, 5),
                       ha='left',
                       fontsize=9,
                       color=color)
        
        # Customize the plot
        plt.xlabel('Session Number', fontsize=12)
        plt.ylabel(y_label, fontsize=12)
        plt.title(title, fontsize=14, pad=15)
        
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(fontsize=10, loc='upper left', bbox_to_anchor=(1, 1))
        
        # Set y-axis range based on metric
        all_values = []
        for model_name in model_names:
            for session in session_nums:
                for user_id, user_data in all_users_data.items():
                    if model_name in user_data and session in user_data[model_name]:
                        if metric in user_data[model_name][session]:
                            all_values.append(user_data[model_name][session][metric])
        
        # Calculate dynamic min_y with 30% padding (but not below 0)
        min_val = min(all_values) if all_values else 0
        padding = 30  # 30% padding
        min_y = max(min_val - padding, 0)
        plt.ylim(min_y, 100)
        
        # Set appropriate tick spacing based on the y-axis range
        tick_spacing = 5 if (100 - min_y) <= 50 else 10
        plt.yticks(range(int(min_y), 101, tick_spacing))
        
        # Set x-axis to show all session numbers
        plt.xlim(min(session_nums) - 0.5, max(session_nums) + 0.5)
        plt.xticks(session_nums)
        
        # Add some padding and adjust layout
        plt.margins(x=0.1)
        plt.tight_layout()
        
        # Save the plot
        metric_name = metric.lower()
        plot_path = output_dir / f'aggregated_biography_{metric_name}_progression.png'
        plt.savefig(plot_path, bbox_inches='tight', dpi=300)
        print(f"Plot saved: {plot_path}")
        
        plt.close()

def main():
    parser = argparse.ArgumentParser(
        description="Analyze and visualize biography metrics progression")
    parser.add_argument('--user_ids', nargs='+', required=True,
                      help='One or more user IDs to analyze')
    args = parser.parse_args()
    
    # Create base output directory for aggregated plot
    base_output_dir = Path('plots')
    base_output_dir.mkdir(exist_ok=True)
    
    # Store data for all users
    all_users_data = {}
    
    for user_id in args.user_ids:
        print(f"\nAnalyzing biography progression for user: {user_id}")
        metrics_data = load_progression_data(user_id)
        
        if not metrics_data:
            print(f"No biography data found for user {user_id}")
            continue
            
        # Store the metrics data for this user
        all_users_data[user_id] = metrics_data
    
    # Choose plotting based on number of users
    if len(all_users_data) == 1:
        # For single user, plot individual progression
        user_id = next(iter(all_users_data))
        plot_metrics_progression(all_users_data[user_id], user_id)
        plot_memory_counts_progression(all_users_data[user_id], user_id)
        print(f"Plots saved in: plots/{user_id}/")
    elif len(all_users_data) > 1:
        # For multiple users, only plot aggregated progression
        plot_aggregated_metrics_progression(all_users_data, base_output_dir)
        print(f"Aggregated plots saved in: plots/")

if __name__ == '__main__':
    main() 