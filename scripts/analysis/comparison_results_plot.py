#!/usr/bin/env python3
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict
from collections import defaultdict
import seaborn as sns

from comparison_results import load_interview_comparisons, load_biography_comparisons

def calculate_win_rates_by_session(
    user_id: str,
    metric_type: str = "bio"  # "bio" or "interview"
) -> Dict[str, Dict[int, float]]:
    """Calculate win rates for each baseline model across different sessions.
    
    Args:
        user_id: User ID to analyze
        metric_type: Type of metrics to analyze ("bio" or "interview")
        
    Returns:
        Dict mapping model names to {session_id: win_rate} dictionaries
    """
    win_rates = defaultdict(lambda: defaultdict(float))
    
    if metric_type == "bio":
        # Get all biography version directories
        eval_dir = Path("logs") / user_id / "evaluations"
        if not eval_dir.exists():
            return dict(win_rates)
            
        bio_dirs = [d for d in eval_dir.glob("biography_*") if d.is_dir()]
        sessions = sorted([int(d.name.split('_')[1]) for d in bio_dirs])
        
        # Calculate win rates for each session
        for session in sessions:
            results = load_biography_comparisons(user_id, session)
            for model, metrics in results.items():
                total_comparisons = 0
                total_wins = 0
                for criterion in ['Insightfulness', 'Narrativity', 'Coherence']:
                    if criterion in metrics:
                        wins, _, total = metrics[criterion]
                        total_wins += wins
                        total_comparisons += total
                if total_comparisons > 0:
                    win_rates[model][session] = (total_wins / total_comparisons) * 100
                    
    else:  # interview metrics
        # Get all unique session IDs from interview comparisons
        eval_dir = Path("logs") / user_id / "evaluations"
        if not eval_dir.exists():
            return dict(win_rates)
            
        interview_file = eval_dir / "interview_comparisons.csv"
        if not interview_file.exists():
            return dict(win_rates)
            
        df = pd.read_csv(interview_file)
        sessions = sorted(df['Session ID'].unique())
        
        # Calculate win rates for each session
        for session in sessions:
            results = load_interview_comparisons(user_id, session)
            for model, metrics in results.items():
                total_comparisons = 0
                total_wins = 0
                for criterion in ['Smooth Score', 'Flexibility Score', 
                                  'Comforting Score']:
                    if criterion in metrics:
                        wins, _, total = metrics[criterion]
                        total_wins += wins
                        total_comparisons += total
                if total_comparisons > 0:
                    win_rates[model][session] = (total_wins / total_comparisons) * 100
    
    return dict(win_rates)

def plot_metric_progression(
    user_id: str,
    metric_type: str,
    metric_name: str
) -> None:
    """Create progression plot for a specific metric.
    
    Args:
        user_id: User ID to analyze
        metric_type: Type of metrics ("bio" or "interview")
        metric_name: Name of the specific metric to plot
    """
    # Set up the plot style - use a specific seaborn style
    plt.style.use('seaborn-v0_8-darkgrid')  # Changed from just 'seaborn'
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Define colors for different baseline models
    colors = sns.color_palette("husl", 8)
    
    # Get win rates data
    if metric_type == "bio":
        eval_dir = Path("logs") / user_id / "evaluations"
        bio_dirs = [d for d in eval_dir.glob("biography_*") if d.is_dir()]
        sessions = sorted([int(d.name.split('_')[1]) for d in bio_dirs])
        
        # Get data for each session
        model_data = defaultdict(lambda: defaultdict(float))
        for session in sessions:
            results = load_biography_comparisons(user_id, session)
            for model, metrics in results.items():
                if metric_name in metrics:
                    wins, _, total = metrics[metric_name]
                    if total > 0:
                        model_data[model][session] = (wins / total) * 100
    else:
        eval_dir = Path("logs") / user_id / "evaluations"
        interview_file = eval_dir / "interview_comparisons.csv"
        df = pd.read_csv(interview_file)
        sessions = sorted(df['Session ID'].unique())
        
        # Get data for each session
        model_data = defaultdict(lambda: defaultdict(float))
        for session in sessions:
            results = load_interview_comparisons(user_id, session)
            for model, metrics in results.items():
                metric_key = f"{metric_name} Score"
                if metric_key in metrics:
                    wins, _, total = metrics[metric_key]
                    if total > 0:
                        model_data[model][session] = (wins / total) * 100
    
    # Plot lines for each baseline model
    for i, (model, data) in enumerate(model_data.items()):
        sessions = sorted(data.keys())
        win_rates = [data[s] for s in sessions]
        ax.plot(sessions, win_rates, marker='o', label=model, color=colors[i])
    
    # Add dashed red line at 50%
    ax.axhline(y=50, color='red', linestyle='--', alpha=0.5, label='Tie Line')
    
    # Customize the plot
    ax.set_xlabel('Session ID')
    ax.set_ylabel('Win Rate (%)')
    title = f"{'Biography' if metric_type == 'bio' else 'Interview'} " \
            f"{metric_name} Win Rate Progression"
    ax.set_title(title)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend(title='Comparison Models', bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Set y-axis limits
    ax.set_ylim(0, 100)
    
    # Add x-axis ticks for each session
    ax.set_xticks(sessions)
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    # Save the plot to /plots/{user_id} directory
    output_dir = Path("plots") / user_id
    output_dir.mkdir(parents=True, exist_ok=True)
    metric_filename = f"compare_{'bio' if metric_type == 'bio' \
                                 else 'interview'}_{metric_name.lower()}_progression.png"
    plt.savefig(output_dir / metric_filename, bbox_inches='tight', dpi=300)
    plt.close()

def main():
    parser = argparse.ArgumentParser(
        description="Generate progression plots for comparison metrics")
    parser.add_argument('--user_ids', nargs='+', required=True,
                      help='One or more user IDs to analyze')
    args = parser.parse_args()
    
    # Biography metrics
    bio_metrics = ['Insightfulness', 'Narrativity', 'Coherence']
    
    # Interview metrics
    interview_metrics = ['Smooth', 'Flexibility', 'Comforting']
    
    for user_id in args.user_ids:
        print(f"\nGenerating plots for user: {user_id}")
        
        # Generate biography metric plots
        for metric in bio_metrics:
            print(f"Plotting biography {metric} progression...")
            plot_metric_progression(user_id, "bio", metric)
        
        # Generate interview metric plots
        for metric in interview_metrics:
            print(f"Plotting interview {metric} progression...")
            plot_metric_progression(user_id, "interview", metric)
        
        print(f"Completed plotting for user {user_id}")

if __name__ == '__main__':
    main() 