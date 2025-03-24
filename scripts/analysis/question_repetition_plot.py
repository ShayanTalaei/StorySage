#!/usr/bin/env python3
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, Optional
import numpy as np

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

def plot_session_repetition(df: pd.DataFrame, session_id: int, model_name: str, 
                          output_dir: Path, color: str):
    """Plot question repetition pattern for a single session.
    
    Args:
        df: DataFrame with question similarity data
        session_id: Session ID to plot
        model_name: Name of the model
        output_dir: Directory to save the plot
        color: Color to use for the plot
    """
    # Filter data for the session
    session_data = df[df['Session ID'] == session_id].copy()
    if session_data.empty:
        return
    
    # Create turn numbers (1-based index)
    session_data['Turn'] = range(1, len(session_data) + 1)
    
    plt.figure(figsize=(12, 4))
    
    # Plot points and connecting lines
    plt.plot(session_data['Turn'], session_data['Is Duplicate'].astype(int),
            color=color, marker='o', linestyle='-', markersize=8,
            label=model_name, linewidth=2, alpha=0.7)
    
    # Customize the plot
    plt.yticks([0, 1], ['Non-Duplicate', 'Duplicate'])
    plt.xlabel('Turn Number', fontsize=12)
    plt.title(f'Question Repetition Pattern - Session {session_id}', 
             fontsize=14, pad=15)
    
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=10, loc='center left', bbox_to_anchor=(1, 0.5))
    
    # Set x-axis to show all turn numbers
    plt.xlim(0.5, len(session_data) + 0.5)
    plt.xticks(session_data['Turn'])
    
    # Add some padding
    plt.margins(y=0.2)
    plt.tight_layout()
    
    # Save the plot
    plot_path = output_dir / f'question_repetition_session_{session_id}.png'
    plt.savefig(plot_path, bbox_inches='tight', dpi=300)
    print(f"Plot saved: {plot_path}")
    
    plt.close()

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

def plot_progression(metrics_data: Dict[str, Dict[int, float]], user_id: str, 
                    output_dir: Path):
    """Plot how repetition rates change across sessions.
    
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
    plt.ylabel('Question Repetition Rate (%)', fontsize=12)
    plt.title('Question Repetition Rate Progression', fontsize=14, pad=15)
    
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=10, loc='upper left', bbox_to_anchor=(1, 1))
    
    # Set y-axis range from 0 to 100
    plt.ylim(0, 100)
    
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

def main():
    parser = argparse.ArgumentParser(
        description="Visualize question repetition patterns")
    parser.add_argument('--user_ids', nargs='+', required=True,
                      help='One or more user IDs to analyze')
    args = parser.parse_args()
    
    # Define colors that will be used for models
    colors = [
        '#2E86C1',  # Blue
        '#E74C3C',  # Red
        '#27AE60',  # Green
        '#8E44AD',  # Purple
        '#F39C12',  # Orange
        '#16A085',  # Teal
        '#D35400',  # Dark Orange
        '#7F8C8D',  # Gray
        '#8E44AD',  # Purple
        '#2980B9',  # Light Blue
        '#C0392B',  # Dark Red
        '#27AE60'   # Light Green
    ]
    
    for user_id in args.user_ids:
        print(f"\nAnalyzing question repetition for user: {user_id}")
        
        # Create output directory
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
        
        # Create color mapping based on sorted model names
        sorted_models = sorted(model_data.keys())
        model_to_color = {model: colors[i % len(colors)] 
                         for i, model in enumerate(sorted_models)}
        
        # Plot repetition patterns for each session
        all_sessions = {session_id for df in model_data.values() 
                       for session_id in df['Session ID'].unique()}
        
        for session_id in sorted(all_sessions):
            plt.figure(figsize=(12, 4))
            
            # Plot all models on the same figure
            for model_name in sorted_models:
                df = model_data[model_name]
                color = model_to_color[model_name]
                plot_session_repetition(df, session_id, model_name, output_dir, color)
        
        # Calculate and plot progression across sessions
        progression_data = {
            model_name: calculate_session_rates(df)
            for model_name, df in model_data.items()
        }
        plot_progression(progression_data, user_id, output_dir)
        
        print(f"\nAll plots have been saved in: plots/{user_id}/")

if __name__ == '__main__':
    main() 