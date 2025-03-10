#!/usr/bin/env python3
import os
import argparse
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

def load_interview_comparisons(user_id: str) -> Dict[str, Dict[str, Tuple[int, int, int]]]:
    """Load interview comparison results for a user.
    
    Args:
        user_id: The user ID to analyze
        
    Returns:
        Dictionary mapping baseline models to their metrics (wins, ties, total)
    """
    results = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))  # [wins, ties, total]
    
    # Load from the main logs directory
    comparison_file = Path("logs") / user_id / "evaluations" / "interview_comparisons.csv"
    
    if comparison_file.exists():
        df = pd.read_csv(comparison_file)
        
        for _, row in df.iterrows():
            # Determine which model is baseline and get voting results
            if row['Model A'] == 'ours':
                baseline_model = row['Model B']
                for criterion in ['Smooth Score', 'Flexibility Score', 
                                'Quality Score', 'Comforting Score']:
                    winner_col = f'{criterion} Winner'
                    if winner_col in df.columns:
                        winner = row[winner_col]
                        results[baseline_model][criterion][2] += 1  # Increment total
                        if winner == 'A':  # Our model won
                            results[baseline_model][criterion][0] += 1  # Increment wins
                        elif winner == 'Tie':  # Tie
                            results[baseline_model][criterion][1] += 1  # Increment ties
            else:
                baseline_model = row['Model A']
                for criterion in ['Smooth Score', 'Flexibility Score', 
                                'Quality Score', 'Comforting Score']:
                    winner_col = f'{criterion} Winner'
                    if winner_col in df.columns:
                        winner = row[winner_col]
                        results[baseline_model][criterion][2] += 1  # Increment total
                        if winner == 'B':  # Our model won
                            results[baseline_model][criterion][0] += 1  # Increment wins
                        elif winner == 'Tie':  # Tie
                            results[baseline_model][criterion][1] += 1  # Increment ties
    
    return results

def load_biography_comparisons(user_id: str) -> Dict[str, Dict[str, Tuple[int, int, int]]]:
    """Load biography comparison results for a user.
    
    Args:
        user_id: The user ID to analyze
        
    Returns:
        Dictionary mapping baseline models to their metrics (wins, ties, total)
    """
    results = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))  # [wins, ties, total]
    
    # Find the latest biography version directory
    eval_dir = Path("logs") / user_id / "evaluations"
    
    if not eval_dir.exists():
        return results
        
    bio_dirs = [d for d in eval_dir.glob("biography_*") if d.is_dir()]
    if not bio_dirs:
        return results
        
    latest_bio_dir = max(bio_dirs, key=lambda d: int(d.name.split('_')[1]))
    
    # Load comparison results
    comparison_file = latest_bio_dir / "biography_comparisons.csv"
    
    if comparison_file.exists():
        df = pd.read_csv(comparison_file)
        
        for _, row in df.iterrows():
            # Determine which model is baseline and get voting results
            if row['Model A'] == 'ours':
                baseline_model = row['Model B']
                for criterion in ['Insightfulness', 'Narrativity', 'Coherence']:
                    winner_col = f'{criterion} Winner'
                    if winner_col in df.columns:
                        winner = row[winner_col]
                        results[baseline_model][criterion][2] += 1  # Increment total
                        if winner == 'A':  # Our model won
                            results[baseline_model][criterion][0] += 1  # Increment wins
                        elif winner == 'Tie':  # Tie
                            results[baseline_model][criterion][1] += 1  # Increment ties
            else:
                baseline_model = row['Model A']
                for criterion in ['Insightfulness', 'Narrativity', 'Coherence']:
                    winner_col = f'{criterion} Winner'
                    if winner_col in df.columns:
                        winner = row[winner_col]
                        results[baseline_model][criterion][2] += 1  # Increment total
                        if winner == 'B':  # Our model won
                            results[baseline_model][criterion][0] += 1  # Increment wins
                        elif winner == 'Tie':  # Tie
                            results[baseline_model][criterion][1] += 1  # Increment ties
    
    return results

def format_table_cell(wins: int, ties: int, total: int) -> str:
    """Format a table cell with win rate and loss rate.
    
    Args:
        wins: Number of wins
        ties: Number of ties
        total: Total number of comparisons
        
    Returns:
        Formatted string with win rate and loss rate
    """
    if total == 0:
        return "- -"
    
    win_rate = wins / total
    loss_rate = (total - wins - ties) / total
    
    return f"{win_rate:.2f} {loss_rate:.2f}"

def display_results(interview_results: Dict[str, Dict[str, List[int]]], 
                   biography_results: Dict[str, Dict[str, List[int]]]) -> None:
    """Display comparison results in a formatted table.
    
    Args:
        interview_results: Dictionary of interview comparison results
        biography_results: Dictionary of biography comparison results
    """
    print("\n" + "=" * 120)
    print("COMPARISON RESULTS")
    print("=" * 120)
    
    # Print header
    print(f"{'':20} | {'Smooth':^12} | {'Flexibility':^12} | {'Quality':^12} | " + 
          f"{'Comfort':^12} | {'Insight':^12} | {'Narrative':^12} | {'Coherence':^12}")
    print(f"{'Ours vs Baselines':20} | {'W':>3} {'L':>3} | {'W':>3} {'L':>3} | {'W':>3} {'L':>3} | " + 
          f"{'W':>3} {'L':>3} | {'W':>3} {'L':>3} | {'W':>3} {'L':>3} | {'W':>3} {'L':>3}")
    print("-" * 120)
    
    # Combine all baseline models
    all_models = set(interview_results.keys()) | set(biography_results.keys())
    
    for model in sorted(all_models):
        # Get interview metrics
        smooth_stats = interview_results[model].get('Smooth Score', [0, 0, 0])
        flex_stats = interview_results[model].get('Flexibility Score', [0, 0, 0])
        quality_stats = interview_results[model].get('Quality Score', [0, 0, 0])
        comfort_stats = interview_results[model].get('Comforting Score', [0, 0, 0])
        
        # Get biography metrics
        insight_stats = biography_results[model].get('Insightfulness', [0, 0, 0])
        narrative_stats = biography_results[model].get('Narrativity', [0, 0, 0])
        coherence_stats = biography_results[model].get('Coherence', [0, 0, 0])
        
        # Format the row
        print(f"{model:20} | {format_table_cell(*smooth_stats):^12} | " +
              f"{format_table_cell(*flex_stats):^12} | " +
              f"{format_table_cell(*quality_stats):^12} | " +
              f"{format_table_cell(*comfort_stats):^12} | " +
              f"{format_table_cell(*insight_stats):^12} | " +
              f"{format_table_cell(*narrative_stats):^12} | " +
              f"{format_table_cell(*coherence_stats):^12}")
    
    print("=" * 120)
    print("W = Win Rate, L = Loss Rate (Ties are counted separately but not displayed)")
    print("=" * 120)

def main():
    parser = argparse.ArgumentParser(
        description="Display comparison results in a formatted table")
    parser.add_argument('--user_ids', nargs='+', required=True,
                      help='One or more user IDs to analyze')
    args = parser.parse_args()
    
    # Aggregate results across all users
    all_interview_results = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    all_biography_results = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    
    for user_id in args.user_ids:
        # Load results for this user
        interview_results = load_interview_comparisons(user_id)
        biography_results = load_biography_comparisons(user_id)
        
        # Aggregate results
        for model in interview_results:
            for criterion, stats in interview_results[model].items():
                all_interview_results[model][criterion][0] += stats[0]  # Add wins
                all_interview_results[model][criterion][1] += stats[1]  # Add ties
                all_interview_results[model][criterion][2] += stats[2]  # Add total
        
        for model in biography_results:
            for criterion, stats in biography_results[model].items():
                all_biography_results[model][criterion][0] += stats[0]  # Add wins
                all_biography_results[model][criterion][1] += stats[1]  # Add ties
                all_biography_results[model][criterion][2] += stats[2]  # Add total
    
    # Display the aggregated results
    display_results(all_interview_results, all_biography_results)

if __name__ == '__main__':
    main() 