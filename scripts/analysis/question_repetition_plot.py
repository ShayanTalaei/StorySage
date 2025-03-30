#!/usr/bin/env python3
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, Optional
from statistics import mean

def load_question_data(user_id: str, model_name: Optional[str] = None) -> pd.DataFrame:
    """Load question similarity data for a user.
    
    Args:
        user_id: The user ID to analyze
        model_name: Optional model name for baseline models
        
    Returns:
        DataFrame with question similarity data
    """
    # Determine the logs directory based on model name
    if model_name:
        logs_dir = Path(f"logs_{model_name}")
    else:
        logs_dir = Path("logs")
    
    # Find the question similarity file
    similarity_file = logs_dir / user_id / "evaluations" / "question_similarity.csv"
    
    if not similarity_file.exists():
        print(f"Question similarity file not found: {similarity_file}")
        return pd.DataFrame()
    
    # Load the data
    try:
        df = pd.read_csv(similarity_file)
        df['model'] = 'ours' if model_name is None else model_name
        # Convert string "True"/"False" to boolean values
        df['Is Duplicate'] = df['Is Duplicate'].apply(lambda x: x == "True" or x is True)
        return df
    except Exception as e:
        print(f"Error loading question similarity data: {e}")
        return pd.DataFrame()

def calculate_session_rates(df: pd.DataFrame) -> Dict[int, float]:
    """Calculate repetition rates for each session.
    
    Args:
        df: DataFrame with question similarity data
        
    Returns:
        Dictionary mapping session IDs to their repetition rates
    """
    rates = {}
    for session_id in df['Session ID'].unique():
        session_data = df[df['Session ID'] == session_id]
        total = len(session_data)
        duplicates = session_data['Is Duplicate'].sum()
        rates[session_id] = (duplicates / total) if total > 0 else 0
    return rates

def calculate_accumulated_rates(df: pd.DataFrame) -> Dict[int, float]:
    """Calculate accumulated repetition rates up to each session.
    
    Args:
        df: DataFrame with question similarity data
        
    Returns:
        Dictionary mapping session IDs to their accumulated repetition rates
    """
    rates = {}
    total_questions = 0
    total_duplicates = 0
    
    for session_id in sorted(df['Session ID'].unique()):
        session_data = df[df['Session ID'] == session_id]
        total_questions += len(session_data)
        total_duplicates += session_data['Is Duplicate'].sum()
        rates[session_id] = (total_duplicates / total_questions) if total_questions > 0 \
              else 0
    return rates

def plot_progression(metrics_data: Dict[str, Dict[int, float]], user_id: str, 
                    output_dir: Path):
    """Plot how repetition rates change across sessions.
    
    Args:
        metrics_data: Dictionary mapping model names to their session rates
        user_id: ID of the user being analyzed
        output_dir: Directory to save the plot
    
    Deprecated:
        Calculating the accumulated rates instead of the session rates.
    """
    if not metrics_data:
        return
        
    # Colors for different models
    colors = ['#2E86C1', '#E74C3C', '#27AE60', '#8E44AD', '#F39C12', '#16A085']
    
    plt.figure(figsize=(12, 6))
    
    # Plot each model's progression
    for (model_name, rates), color in zip(metrics_data.items(), colors):
        if not rates:
            continue
        
        # Get session numbers and rates, sorted by session number
        session_nums = sorted(rates.keys())
        values = [rates[num] * 100 for num in session_nums]  # Convert to percentage
        
        # Plot progression
        plt.plot(session_nums, values, marker='o', linestyle='-', color=color,
                label=f'{model_name}', linewidth=2, markersize=6)
        
        # Annotate all values
        for x, y in zip(session_nums, values):
            plt.annotate(f'{y:.1f}%', 
                       (x, y),
                       textcoords="offset points",
                       xytext=(5, 5),
                       ha='left',
                       fontsize=9,
                       color=color)
    
    # Customize the plot
    plt.xlabel('Session Number', fontsize=12)
    plt.ylabel('Question Repetition Rate (%)', fontsize=12)
    plt.title('Question Repetition Rate Progression', fontsize=14, pad=15)
    
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=10, loc='upper left', bbox_to_anchor=(1, 1))
    
    # Set y-axis range from 0 to 100 with ticks every 10%
    plt.ylim(0, 100)
    plt.yticks(range(0, 101, 10))
    
    # Set x-axis to show all session numbers
    all_sessions = {num for rates in metrics_data.values() for num in rates.keys()}
    plt.xlim(min(all_sessions) - 0.5, max(all_sessions) + 0.5)
    plt.xticks(sorted(all_sessions))
    
    # Add some padding and adjust layout
    plt.margins(x=0.1)
    plt.tight_layout()
    
    # Save the plot
    plot_path = output_dir / 'question_repetition_progression.png'
    plt.savefig(plot_path, bbox_inches='tight', dpi=300)
    print(f"Plot saved: {plot_path}")
    
    plt.close()

def plot_accumulated_progression(metrics_data: Dict[str, Dict[int, float]], user_id: str, 
                               output_dir: Path):
    """Plot how accumulated repetition rates change across sessions.
    
    Args:
        metrics_data: Dictionary mapping model names to their session rates
        user_id: ID of the user being analyzed
        output_dir: Directory to save the plot
    """
    if not metrics_data:
        return
        
    # Colors for different models
    colors = ['#2E86C1', '#E74C3C', '#27AE60', '#8E44AD', '#F39C12', '#16A085']
    
    plt.figure(figsize=(12, 6))
    
    # Plot each model's progression
    for (model_name, rates), color in zip(metrics_data.items(), colors):
        if not rates:
            continue
        
        # Get session numbers and rates, sorted by session number
        session_nums = sorted(rates.keys())
        values = [rates[num] * 100 for num in session_nums]  # Convert to percentage
        
        # Plot progression
        plt.plot(session_nums, values, marker='o', linestyle='-', color=color,
                label=f'{model_name}', linewidth=2, markersize=6)
        
        # Annotate all values
        for x, y in zip(session_nums, values):
            plt.annotate(f'{y:.1f}%', 
                       (x, y),
                       textcoords="offset points",
                       xytext=(5, 5),
                       ha='left',
                       fontsize=9,
                       color=color)
    
    # Customize the plot
    plt.xlabel('Session Number', fontsize=12)
    plt.ylabel('Accumulated Question Repetition Rate (%)', fontsize=12)
    plt.title('Accumulated Question Repetition Rate Progression', fontsize=14, pad=15)
    
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=10, loc='upper left', bbox_to_anchor=(1, 1))
    
    # Set y-axis range from 0 to 100 with ticks every 10%
    plt.ylim(0, 100)
    plt.yticks(range(0, 101, 10))
    
    # Set x-axis to show all session numbers
    all_sessions = {num for rates in metrics_data.values() for num in rates.keys()}
    plt.xlim(min(all_sessions) - 0.5, max(all_sessions) + 0.5)
    plt.xticks(sorted(all_sessions))
    
    # Add some padding and adjust layout
    plt.margins(x=0.1)
    plt.tight_layout()
    
    # Save the plot
    plot_path = output_dir / 'accumulated_question_repetition_progression.png'
    plt.savefig(plot_path, bbox_inches='tight', dpi=300)
    print(f"Plot saved: {plot_path}")
    
    plt.close()

def plot_aggregated_users_progression(all_users_data: Dict[str, Dict[str, Dict[int, float]]], 
                                    output_dir: Path):
    """Plot average accumulated repetition rates across all users.
    
    Args:
        all_users_data: Dictionary mapping user_ids to their model data
                       {user_id: {model_name: {session_id: rate}}}
        output_dir: Directory to save the plot
    """
    if not all_users_data:
        return
        
    # Colors for different models
    colors = ['#2E86C1', '#E74C3C', '#27AE60', '#8E44AD', '#F39C12', '#16A085']
    
    plt.figure(figsize=(12, 6))
    
    # Get all model names from the first user's data
    first_user = next(iter(all_users_data.values()))
    model_names = list(first_user.keys())
    
    # Get all session numbers (should be same for all users)
    first_model = next(iter(first_user.values()))
    session_nums = sorted(first_model.keys())
    
    # Calculate average rates across users for each model and session
    for model_name, color in zip(model_names, colors):
        # For each session, get the rate from all users and calculate mean
        avg_values = []
        for session in session_nums:
            rates = [user_data[model_name][session] * 100 
                    for user_data in all_users_data.values()]
            avg_values.append(mean(rates))
        
        # Plot progression
        plt.plot(session_nums, avg_values, marker='o', linestyle='-', color=color,
                label=f'{model_name}', linewidth=2, markersize=6)
        
        # Annotate values
        for x, y in zip(session_nums, avg_values):
            plt.annotate(f'{y:.1f}%', 
                       (x, y),
                       textcoords="offset points",
                       xytext=(5, 5),
                       ha='left',
                       fontsize=9,
                       color=color)
    
    # Customize the plot
    plt.xlabel('Session Number', fontsize=12)
    plt.ylabel('Average Accumulated Question Repetition Rate (%)', fontsize=12)
    plt.title('Average Accumulated Question Repetition Rate Across Users', fontsize=14, pad=15)
    
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=10, loc='upper left', bbox_to_anchor=(1, 1))
    
    # Set y-axis range from 0 to 100 with ticks every 10%
    plt.ylim(0, 100)
    plt.yticks(range(0, 101, 10))
    
    # Set x-axis to show all session numbers
    plt.xlim(min(session_nums) - 0.5, max(session_nums) + 0.5)
    plt.xticks(session_nums)
    
    # Add some padding and adjust layout
    plt.margins(x=0.1)
    plt.tight_layout()
    
    # Save the plot
    plot_path = output_dir / 'aggregated_question_repetition_progression.png'
    plt.savefig(plot_path, bbox_inches='tight', dpi=300)
    print(f"Plot saved: {plot_path}")
    
    plt.close()

def main():
    parser = argparse.ArgumentParser(
        description="Visualize question repetition patterns")
    parser.add_argument('--user_ids', nargs='+', required=True,
                      help='One or more user IDs to analyze')
    args = parser.parse_args()
    
    # Create base output directory for aggregated plot
    base_output_dir = Path('plots')
    base_output_dir.mkdir(exist_ok=True)
    
    # Store data for all users
    all_users_data = {}
    
    for user_id in args.user_ids:
        print(f"\nAnalyzing question repetition for user: {user_id}")
        
        # Create output directory for individual user plots
        output_dir = Path('plots') / user_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load data for all models
        model_data = {}
        
        # Load our model's data
        our_df = load_question_data(user_id)
        if not our_df.empty:
            model_data['ours'] = our_df
        
        # Load baseline models' data
        for dir_name in Path('.').glob('logs_*'):
            if dir_name.is_dir():
                model_name = dir_name.name[5:]  # Remove 'logs_' prefix
                baseline_df = load_question_data(user_id, model_name)
                if not baseline_df.empty:
                    model_data[model_name] = baseline_df
        
        if not model_data:
            print(f"No question data found for user {user_id}")
            continue
        
        # Calculate accumulated progression for individual user
        accumulated_data = {
            model_name: calculate_accumulated_rates(df)
            for model_name, df in model_data.items()
        }
        
        # Store the accumulated data for this user
        all_users_data[user_id] = accumulated_data
    
    # Choose plotting based on number of users
    if len(all_users_data) == 1:
        # For single user, plot individual progression
        user_id = next(iter(all_users_data))
        output_dir = Path('plots') / user_id
        plot_accumulated_progression(all_users_data[user_id], user_id, output_dir)
        print(f"Plot saved in: plots/{user_id}/")
    elif len(all_users_data) > 1:
        # For multiple users, only plot aggregated progression
        plot_aggregated_users_progression(all_users_data, base_output_dir)
        print(f"Aggregated plot saved in: plots/")

if __name__ == '__main__':
    main() 