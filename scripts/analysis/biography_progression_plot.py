#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import re
from typing import Dict
import numpy as np

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
            total_memories = df.loc[df['Metric'] == 'Total Memories',
                                     'Value'].iloc[0]
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
        plt.figure(figsize=(8, 6))
        
        # Plot each model's progression
        for (model_name, sessions), color in zip(metrics_data.items(), colors):
            if not sessions:
                continue
            
            # Get all session numbers and values, sorted by session number
            session_nums = sorted(sessions.keys())
            
            # Filter to only include sessions that have the current metric
            valid_sessions = [num for num in session_nums \
                              if metric in sessions[num]]
            values = [sessions[num][metric] for num in valid_sessions]
            
            if not values:
                continue
            
            # Use "Baseline" for any model that isn't "StorySage"
            display_name = model_name if model_name == "ours" else "Baseline"
            
            # Plot progression
            plt.plot(valid_sessions, values, marker='o', 
                     linestyle='-', color=color,
                    label=f'{display_name}', linewidth=2, markersize=6)
            
            # Annotate final value
            if values:
                plt.annotate(f'{values[-1]:.1f}%', 
                           (valid_sessions[-1], values[-1]),
                           textcoords="offset points",
                           xytext=(5, 5),
                           ha='left',
                           fontsize=14,
                           color=color)
        
        # Customize the plot
        plt.xlabel('Session Number', fontsize=18)
        plt.ylabel(y_label, fontsize=18)
        
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(fontsize=16, loc='lower left')
        
        # Set y-axis range based on metric
        all_values = [val for model_data in metrics_data.values() 
                     for session in model_data.values() 
                     if metric in session
                     for val in [session[metric]]]
        
        # Set fixed y-axis range for memory coverage, dynamic for groundedness
        if metric == 'completeness':
            min_y = 30
            plt.ylim(30, 100)
            tick_spacing = 10
        else:
            # Calculate dynamic min_y with 30% padding (but not below 0)
            min_val = min(all_values) if all_values else 0
            padding = 30  # 30% padding
            min_y = max(min_val - padding, 0)
            plt.ylim(min_y, 100)
            # Set appropriate tick spacing based on the y-axis range
            tick_spacing = 5 if (100 - min_y) <= 50 else 10
        
        plt.yticks(range(int(min_y), 101, tick_spacing), fontsize=16)
        
        # Set x-axis to show all session numbers
        all_sessions = {num for model_data in metrics_data.values() 
                       for num in model_data.keys()}
        if all_sessions:  # Check if there are any sessions
            plt.xlim(min(all_sessions) - 0.5, max(all_sessions) + 0.5)
            plt.xticks(sorted(all_sessions), fontsize=16)
        
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
    
    # Create a single plot for all models
    plt.figure(figsize=(8, 6))
    
    # Define a color palette for different models
    colors = ['#2E86C1', '#E74C3C', '#27AE60', '#8E44AD', '#F39C12', '#16A085', '#D35400']
    
    # Track all values for y-axis scaling
    all_values = []
    all_session_nums = set()
    
    # Plot each model
    for i, (model_name, sessions) in enumerate(metrics_data.items()):
        if not sessions:
            continue
            
        # Get color for this model (cycle through colors if needed)
        color = colors[i % len(colors)]
        
        # Get all session numbers and values, sorted by session number
        session_nums = sorted(sessions.keys())
        all_session_nums.update(session_nums)
        
        total_memories = [sessions[num]['total_memories'] for num in session_nums 
                         if 'total_memories' in sessions[num]]
        referenced_memories = [sessions[num]['referenced_memories'] for num in session_nums 
                             if 'referenced_memories' in sessions[num]]
        
        if not total_memories or not referenced_memories:
            continue
        
        all_values.extend(total_memories + referenced_memories)
        
        # Plot total memories with dashed line
        plt.plot(session_nums, total_memories, marker='o', linestyle='--', color=color,
                label=f'{"StorySage" if model_name == "ours" else "Baseline"} - Mem. stored in M', linewidth=2, markersize=6)
        
        # Plot referenced memories with solid line
        plt.plot(session_nums, referenced_memories, marker='s', linestyle='-', color=color,
                label=f'{"StorySage" if model_name == "ours" else "Baseline"} - Mem. referenced in B', linewidth=2, markersize=5)
        
        # Annotate final values
        plt.annotate(f'{total_memories[-1]}', 
                    (session_nums[-1], total_memories[-1]),
                    textcoords="offset points",
                    xytext=(5, 5),
                    ha='left',
                    fontsize=14,
                    color=color)
        plt.annotate(f'{referenced_memories[-1]}', 
                    (session_nums[-1], referenced_memories[-1]),
                    textcoords="offset points",
                    xytext=(5, 5),
                    ha='left',
                    fontsize=14,
                    color=color)
    
    # Customize the plot
    plt.xlabel('Session Number', fontsize=18)
    plt.ylabel('Number of Memories', fontsize=18)
    
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=16, loc='upper left')
    
    # Set y-axis range
    min_y = max(min(all_values) - 2, 0) if all_values else 0
    max_y = max(all_values) + 2 if all_values else 10
    plt.ylim(min_y, max_y)
    
    # Set x-axis to show all session numbers
    all_session_nums = sorted(all_session_nums)
    if all_session_nums:
        plt.xlim(min(all_session_nums) - 0.5, max(all_session_nums) + 0.5)
        plt.xticks(all_session_nums, fontsize=16)
    
    # Add padding and adjust layout
    plt.margins(x=0.1)
    plt.tight_layout()
    
    # Save the plot
    plot_path = output_dir / f'biography_memory_counts_all_models.png'
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
        plt.figure(figsize=(8, 6))
        
        # Plot each model's progression
        for model_name, color in zip(model_names, colors):
            # Calculate average values and standard deviations across users for each session
            avg_values = []
            std_values = []
            valid_sessions = []
            
            for session in session_nums:
                values = [user_data[model_name][session][metric] 
                         for user_data in all_users_data.values()
                         if metric in user_data[model_name][session]]
                if values:
                    avg_values.append(sum(values) / len(values))
                    std_values.append(np.std(values))
                    valid_sessions.append(session)
            
            if not avg_values:
                continue
            
            # Use "Baseline" for any model that isn't "StorySage"
            display_name = "StorySage" if model_name == "ours" else "Baseline"
            
            # Plot progression with mean line
            plt.plot(valid_sessions, avg_values, marker='o', 
                    linestyle='-', color=color,
                    label=f'{display_name}', linewidth=2, markersize=6)
            
            # Add standard deviation band
            plt.fill_between(valid_sessions, 
                           [max(0, avg - std) for avg, std in zip(avg_values, std_values)],
                           [min(100, avg + std) for avg, std in zip(avg_values, std_values)],
                           color=color, alpha=0.2)
            
            # Annotate final value
            plt.annotate(f'{avg_values[-1]:.1f}%', 
                       (valid_sessions[-1], avg_values[-1]),
                       textcoords="offset points",
                       xytext=(5, 5),
                       ha='left',
                       fontsize=14,
                       color=color)
        
        # Customize the plot
        plt.xlabel('Session Number', fontsize=18)
        plt.ylabel(y_label, fontsize=18)
        
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(fontsize=16, loc='lower left')
        
        # Set y-axis range based on metric
        all_values = []
        for model_name in model_names:
            for session in session_nums:
                for user_data in all_users_data.values():
                    if model_name in user_data and session in user_data[model_name]:
                        if metric in user_data[model_name][session]:
                            all_values.append(user_data[model_name][session][metric])
        
        # Set fixed y-axis range for memory coverage, dynamic for groundedness
        if metric == 'completeness':
            min_y = 30
            plt.ylim(30, 100)
            tick_spacing = 10
        else:
            # Calculate dynamic min_y with 30% padding (but not below 0)
            min_val = min(all_values) if all_values else 0
            padding = 30  # 30% padding
            min_y = max(min_val - padding, 0)
            plt.ylim(min_y, 100)
            # Set appropriate tick spacing based on the y-axis range
            tick_spacing = 5 if (100 - min_y) <= 50 else 10
        
        plt.yticks(range(int(min_y), 101, tick_spacing), fontsize=16)
        
        # Set x-axis to show all session numbers
        plt.xlim(min(session_nums) - 0.5, max(session_nums) + 0.5)
        plt.xticks(session_nums, fontsize=16)
        
        # Add some padding and adjust layout
        plt.margins(x=0.1)
        plt.tight_layout()
        
        # Save the plot
        metric_name = metric.lower()
        plot_path = output_dir / f'aggregated_biography_{metric_name}_progression.png'
        plt.savefig(plot_path, bbox_inches='tight', dpi=300)
        print(f"Plot saved: {plot_path}")
        
        plt.close()

def plot_aggregated_memory_counts_progression(all_users_data: Dict[str, Dict[str, Dict[int, Dict[str, float]]]], 
                                            output_dir: Path):
    """Plot average memory counts across all users.
    
    Args:
        all_users_data: Dictionary mapping user_ids to their model data
                       {user_id: {model_name: {session_id: metrics}}}
        output_dir: Directory to save the plot
    """
    if not all_users_data:
        print("No metrics data available to plot")
        return
    
    # Create a single plot for all models
    plt.figure(figsize=(8, 6))
    
    # Define a color palette for different models
    colors = ['#2E86C1', '#E74C3C', '#27AE60', '#8E44AD', '#F39C12', '#16A085', '#D35400']
    
    # Get all model names from the first user's data
    first_user = next(iter(all_users_data.values()))
    model_names = list(first_user.keys())
    
    # Get all session numbers (should be same for all users)
    all_session_nums = set()
    for user_data in all_users_data.values():
        for model_name, sessions in user_data.items():
            all_session_nums.update(sessions.keys())
    session_nums = sorted(all_session_nums)
    
    # Track all values for y-axis scaling
    all_values = []
    
    # Plot each model
    for i, model_name in enumerate(model_names):
        # Get color for this model (cycle through colors if needed)
        color = colors[i % len(colors)]
        
        # Calculate average values and standard deviations across users for each session
        avg_total_memories = []
        std_total_memories = []
        avg_referenced_memories = []
        std_referenced_memories = []
        valid_sessions = []
        
        for session in session_nums:
            total_values = []
            referenced_values = []
            
            for user_data in all_users_data.values():
                if model_name in user_data and session in user_data[model_name]:
                    if 'total_memories' in user_data[model_name][session]:
                        total_values.append(user_data[model_name][session]['total_memories'])
                    if 'referenced_memories' in user_data[model_name][session]:
                        referenced_values.append(user_data[model_name][session]['referenced_memories'])
            
            if total_values and referenced_values:
                # Convert averages to integers
                avg_total = int(round(sum(total_values) / len(total_values)))
                std_total = np.std(total_values)
                avg_total_memories.append(avg_total)
                std_total_memories.append(std_total)
                
                avg_ref = int(round(sum(referenced_values) / len(referenced_values)))
                std_ref = np.std(referenced_values)
                avg_referenced_memories.append(avg_ref)
                std_referenced_memories.append(std_ref)
                
                valid_sessions.append(session)
        
        if not avg_total_memories or not avg_referenced_memories:
            continue
        
        all_values.extend(avg_total_memories + avg_referenced_memories)
        
        # Plot total memories with dashed line
        plt.plot(valid_sessions, avg_total_memories, marker='o', linestyle='--', color=color,
                label=f'{"StorySage" if model_name == "ours" else "Baseline"} - Mem. stored in M', linewidth=2, markersize=6)
        
        # Add standard deviation band for total memories
        plt.fill_between(valid_sessions, 
                       [max(0, avg - std) for avg, std in zip(avg_total_memories, std_total_memories)],
                       [avg + std for avg, std in zip(avg_total_memories, std_total_memories)],
                       color=color, alpha=0.1)
        
        # Plot referenced memories with solid line
        plt.plot(valid_sessions, avg_referenced_memories, marker='s', linestyle='-', color=color,
                label=f'{"StorySage" if model_name == "ours" else "Baseline"} - Mem. referenced in B', linewidth=2, markersize=5)
        
        # Add standard deviation band for referenced memories
        plt.fill_between(valid_sessions, 
                       [max(0, avg - std) for avg, std in zip(avg_referenced_memories, std_referenced_memories)],
                       [avg + std for avg, std in zip(avg_referenced_memories, std_referenced_memories)],
                       color=color, alpha=0.1)
        
        # Annotate final values with integers instead of decimals
        plt.annotate(f'{avg_total_memories[-1]}', 
                    (valid_sessions[-1], avg_total_memories[-1]),
                    textcoords="offset points",
                    xytext=(5, 5),
                    ha='left',
                    fontsize=14,
                    color=color)
        plt.annotate(f'{avg_referenced_memories[-1]}', 
                    (valid_sessions[-1], avg_referenced_memories[-1]),
                    textcoords="offset points",
                    xytext=(5, 5),
                    ha='left',
                    fontsize=14,
                    color=color)
    
    # Customize the plot
    plt.xlabel('Session Number', fontsize=18)
    plt.ylabel('Number of Memories', fontsize=18)
    
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=16, loc='upper left')
    
    # Set y-axis range
    min_y = max(min(all_values) - 2, 0) if all_values else 0
    max_y = max(all_values) + 2 if all_values else 10
    plt.ylim(min_y, max_y)
    
    # Set x-axis to show all session numbers
    if session_nums:
        plt.xlim(min(session_nums) - 0.5, max(session_nums) + 0.5)
        plt.xticks(session_nums, fontsize=16)
    
    # Add padding and adjust layout
    plt.margins(x=0.1)
    plt.tight_layout()
    
    # Save the plot
    plot_path = output_dir / f'aggregated_biography_memory_counts_all_models.png'
    plt.savefig(plot_path, bbox_inches='tight', dpi=300)
    print(f"Plot saved: {plot_path}")
    
    plt.close()

def count_words_in_biography(bio_file: Path) -> int:
    """Count the number of words in a biography file.
    
    Args:
        bio_file: Path to the biography JSON file
        
    Returns:
        Number of words in the biography
    """
    # First, try to find and use the markdown version
    md_file = bio_file.with_suffix('.md')
    
    if md_file.exists():
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                bio_text = f.read()
            # Count words by splitting on whitespace
            return len(bio_text.split())
        except Exception as e:
            print(f"Error reading markdown biography file {md_file}: {e}")
            # Fall back to JSON if there's an error with the markdown file

def get_biography_word_counts(user_id: str, model_name: str = 'ours') -> Dict[int, int]:
    """Get word counts for each biography version.
    
    Args:
        user_id: The user ID to analyze
        model_name: Name of the model ('ours' or a baseline model name)
        
    Returns:
        Dictionary mapping session numbers to word counts
    """
    word_counts = {}
    
    # Determine the base directory based on model name
    if model_name == 'ours':
        base_dir = Path('data') / user_id
    else:
        base_dir = Path(f'data_{model_name}') / user_id
    
    if not base_dir.exists():
        return word_counts
    
    # Find all biography files
    bio_files = list(base_dir.glob("biography_*.json"))
    
    for bio_file in bio_files:
        # Extract session number from filename
        match = re.search(r'biography_(\d+)\.json', str(bio_file))
        if not match:
            continue
            
        session_num = int(match.group(1))
        word_count = count_words_in_biography(bio_file)
        
        if word_count > 0:
            word_counts[session_num] = word_count
    
    return word_counts

def load_biography_word_counts(user_id: str) -> Dict[str, Dict[int, int]]:
    """Load biography word counts for all models.
    
    Args:
        user_id: The user ID to analyze
        
    Returns:
        Dictionary mapping model names to their session word counts
    """
    model_data = {}
    
    # Load our model's data
    word_counts = get_biography_word_counts(user_id, 'ours')
    if word_counts:
        model_data['ours'] = word_counts
    
    # Load baseline models' data
    for dir_name in os.listdir('.'):
        if dir_name.startswith('data_'):
            model_name = dir_name[5:]  # Remove 'data_' prefix
            word_counts = get_biography_word_counts(user_id, model_name)
            if word_counts:
                model_data[model_name] = word_counts
    
    return model_data

def plot_biography_word_counts(word_counts_data: Dict[str, Dict[int, int]], user_id: str):
    """Plot how biography word counts change across sessions.
    
    Args:
        word_counts_data: Dictionary mapping model names to their session word counts
        user_id: ID of the user being analyzed
    """
    if not word_counts_data:
        print("No biography word count data available to plot")
        return
    
    output_dir = Path('plots') / user_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    plt.figure(figsize=(8, 6))
    
    # Define a color palette for different models
    colors = ['#2E86C1', '#E74C3C', '#27AE60', '#8E44AD', '#F39C12', '#16A085', '#D35400']
    
    # Track all values for y-axis scaling
    all_values = []
    all_session_nums = set()
    
    # Plot each model
    for i, (model_name, sessions) in enumerate(word_counts_data.items()):
        if not sessions:
            continue
            
        # Get color for this model (cycle through colors if needed)
        color = colors[i % len(colors)]
        
        # Get all session numbers and values, sorted by session number
        session_nums = sorted(sessions.keys())
        all_session_nums.update(session_nums)
        
        word_counts = [sessions[num] for num in session_nums]
        
        if not word_counts:
            continue
        
        all_values.extend(word_counts)
        
        # Plot word counts
        plt.plot(session_nums, word_counts, marker='o', linestyle='-', color=color,
                label=f'{"StorySage" if model_name == "ours" else "Baseline"}', linewidth=2, markersize=6)
        
        # Annotate final value
        plt.annotate(f'{word_counts[-1]}', 
                    (session_nums[-1], word_counts[-1]),
                    textcoords="offset points",
                    xytext=(5, 5),
                    ha='left',
                    fontsize=14,
                    color=color)
    
    # Customize the plot
    plt.xlabel('Session Number', fontsize=18)
    plt.ylabel('Word Count', fontsize=18)
    
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=16, loc='upper left')
    
    # Set y-axis range
    min_y = max(min(all_values) - 50, 0) if all_values else 0
    max_y = max(all_values) + 50 if all_values else 500
    plt.ylim(min_y, max_y)
    
    # Set x-axis to show all session numbers
    all_session_nums = sorted(all_session_nums)
    if all_session_nums:
        plt.xlim(min(all_session_nums) - 0.5, max(all_session_nums) + 0.5)
        plt.xticks(all_session_nums, fontsize=16)
    
    # Add padding and adjust layout
    plt.margins(x=0.1)
    plt.tight_layout()
    
    # Save the plot
    plot_path = output_dir / f'biography_word_count_progression.png'
    plt.savefig(plot_path, bbox_inches='tight', dpi=300)
    print(f"Plot saved: {plot_path}")
    
    plt.close()

def plot_aggregated_biography_word_counts(all_users_data: Dict[str, Dict[str, Dict[int, int]]], 
                                        output_dir: Path):
    """Plot average biography word counts across all users.
    
    Args:
        all_users_data: Dictionary mapping user_ids to their model data
                       {user_id: {model_name: {session_id: word_count}}}
        output_dir: Directory to save the plot
    """
    if not all_users_data:
        print("No biography word count data available to plot")
        return
    
    # Create a single plot for all models
    plt.figure(figsize=(8, 6))
    
    # Define a color palette for different models
    colors = ['#2E86C1', '#E74C3C', '#27AE60', '#8E44AD', '#F39C12', '#16A085', '#D35400']
    
    # Get all model names from the first user's data
    first_user = next(iter(all_users_data.values()))
    model_names = list(first_user.keys())
    
    # Get all session numbers
    all_session_nums = set()
    for user_data in all_users_data.values():
        for model_name, sessions in user_data.items():
            all_session_nums.update(sessions.keys())
    session_nums = sorted(all_session_nums)
    
    # Track all values for y-axis scaling
    all_values = []
    
    # Plot each model
    for i, model_name in enumerate(model_names):
        # Get color for this model (cycle through colors if needed)
        color = colors[i % len(colors)]
        
        # Calculate average values and standard deviations
        avg_word_counts = []
        std_word_counts = []
        valid_sessions = []
        
        for session in session_nums:
            word_counts = []
            
            for user_data in all_users_data.values():
                if model_name in user_data and session in user_data[model_name]:
                    word_counts.append(user_data[model_name][session])
            
            if word_counts:
                # Convert average to integer
                avg_count = int(round(sum(word_counts) / len(word_counts)))
                std_count = np.std(word_counts)
                avg_word_counts.append(avg_count)
                std_word_counts.append(std_count)
                valid_sessions.append(session)
        
        if not avg_word_counts:
            continue
        
        all_values.extend(avg_word_counts)
        
        # Plot word counts
        plt.plot(valid_sessions, avg_word_counts, marker='o', 
                 linestyle='-', color=color,
                label=f'{"StorySage" if model_name == "ours" else "Baseline"}', linewidth=2, markersize=6)
        
        # Add standard deviation band
        plt.fill_between(valid_sessions, 
                       [max(0, avg - std) for avg, std in 
                         zip(avg_word_counts, std_word_counts)],
                       [avg + std for avg, std in 
                        zip(avg_word_counts, std_word_counts)],
                       color=color, alpha=0.1)
        
        # Annotate final value
        plt.annotate(f'{avg_word_counts[-1]}', 
                    (valid_sessions[-1], avg_word_counts[-1]),
                    textcoords="offset points",
                    xytext=(5, 5),
                    ha='left',
                    fontsize=14,
                    color=color)
    
    # Customize the plot
    plt.xlabel('Session Number', fontsize=18)
    plt.ylabel('Word Count', fontsize=18)
    
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=16, loc='upper left')
    
    # Set y-axis range
    min_y = max(min(all_values) - 50, 0) if all_values else 0
    max_y = max(all_values) + 50 if all_values else 500
    plt.ylim(min_y, max_y)
    
    # Set x-axis to show all session numbers
    if session_nums:
        plt.xlim(min(session_nums) - 0.5, max(session_nums) + 0.5)
        plt.xticks(session_nums, fontsize=16)
    
    # Add padding and adjust layout
    plt.margins(x=0.1)
    plt.tight_layout()
    
    # Save the plot
    plot_path = output_dir / f'aggregated_biography_word_count_progression.png'
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
    all_users_word_counts = {}
    
    for user_id in args.user_ids:
        print(f"\nAnalyzing biography progression for user: {user_id}")
        metrics_data = load_progression_data(user_id)
        word_counts_data = load_biography_word_counts(user_id)
        
        if not metrics_data and not word_counts_data:
            print(f"No biography data found for user {user_id}")
            continue
            
        # Store the metrics data for this user
        if metrics_data:
            all_users_data[user_id] = metrics_data
        
        # Store the word counts data for this user
        if word_counts_data:
            all_users_word_counts[user_id] = word_counts_data
    
    # Choose plotting based on number of users
    if len(all_users_data) == 1 or len(all_users_word_counts) == 1:
        # For single user, plot individual progression
        user_id = next(iter(all_users_data)) if all_users_data \
              else next(iter(all_users_word_counts))
        
        if user_id in all_users_data:
            plot_metrics_progression(all_users_data[user_id], user_id)
            plot_memory_counts_progression(all_users_data[user_id], user_id)
        
        if user_id in all_users_word_counts:
            plot_biography_word_counts(all_users_word_counts[user_id], user_id)
            
        print(f"Plots saved in: plots/{user_id}/")
    elif len(all_users_data) > 1 or len(all_users_word_counts) > 1:
        # For multiple users, plot aggregated progression
        if all_users_data:
            plot_aggregated_metrics_progression(all_users_data, base_output_dir)
            plot_aggregated_memory_counts_progression(all_users_data, base_output_dir)
        
        if all_users_word_counts:
            plot_aggregated_biography_word_counts(
                all_users_word_counts, base_output_dir)
            
        print(f"Aggregated plots saved in: plots/")

if __name__ == '__main__':
    main() 