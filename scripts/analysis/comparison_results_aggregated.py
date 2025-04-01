#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

import argparse
import pandas as pd
from typing import Dict, List
from collections import defaultdict

def format_table_cell(wins: int, ties: int, total: int) -> str:
    """Format a table cell with win rate and loss rate as percentages."""
    if total == 0:
        return "- -"
    
    win_rate = (wins / total) * 100
    loss_rate = ((total - wins - ties) / total) * 100
    
    return f"{win_rate:.0f} {loss_rate:.0f}"

def display_results(interview_results: Dict[str, Dict[str, List[int]]], 
                   biography_results: Dict[str, Dict[str, List[int]]]) -> None:
    """Display comparison results in a formatted table."""
    # Define column widths
    col_width = 14  # Increased to accommodate longer names
    first_col_width = 20
    
    # Define metrics to display with new names
    interview_metrics = ["Naturalness", "Human Agency", "Comfort"]  # Updated names
    biography_metrics = ["Insight", "Narrative", "Coherence"]
    all_metrics = interview_metrics + biography_metrics
    
    # Calculate total width
    total_width = first_col_width + len(all_metrics) * (col_width + 3) - 1
    
    print("\n" + "=" * total_width)
    print("COMPARISON RESULTS")
    print("=" * total_width)
    
    # Print category headers with adjusted spacing
    category_header = f"{'':{first_col_width}} |"
    category_header += f" {'INTERVIEW METRICS':^{len(interview_metrics)*(col_width+3)-3}} |"
    category_header += f" {'BIOGRAPHY METRICS':^{len(biography_metrics)*(col_width+3)-3}} |"
    print(category_header)
    
    # Print header row with metric names
    header = f"{'':{first_col_width}} |"
    for metric in all_metrics:
        header += f" {metric:^{col_width}} |"
    print(header)
    
    # Print subheader with W/L indicators
    subheader = f"{'Ours vs Baselines':{first_col_width}} |"
    for _ in range(len(all_metrics)):
        subheader += f" {'W':^7}{'L':^7} |"  # Adjusted spacing for W/L
    print(subheader)
    
    # Print separator
    print("-" * total_width)
    
    # Combine all baseline models
    all_models = set(interview_results.keys()) | set(biography_results.keys())
    
    for model in sorted(all_models):
        # Get interview metrics (using original keys from the data)
        smooth_stats = interview_results[model].get('Smooth Score', [0, 0, 0])
        flex_stats = interview_results[model].get('Flexibility Score', [0, 0, 0])
        comfort_stats = interview_results[model].get('Comforting Score', [0, 0, 0])
        
        # Get biography metrics
        insight_stats = biography_results[model].get('Insightfulness', [0, 0, 0])
        narrative_stats = biography_results[model].get('Narrativity', [0, 0, 0])
        coherence_stats = biography_results[model].get('Coherence', [0, 0, 0])
        
        # Format the row with wider columns
        row = f"{model:{first_col_width}} |"
        for stats in [smooth_stats, flex_stats, comfort_stats, 
                     insight_stats, narrative_stats, coherence_stats]:
            row += f" {format_table_cell(*stats):^{col_width}} |"
        print(row)
    
    print("=" * total_width)
    print("W = Win Rate, L = Loss Rate (Ties are counted separately but not displayed)")
    print("=" * total_width)

def main():
    parser = argparse.ArgumentParser(
        description="Display comparison results aggregated across all sessions and users")
    parser.add_argument('--user_ids', nargs='+', required=True,
                      help='One or more user IDs to analyze')
    args = parser.parse_args()
    
    # First, collect all comparison data from all users
    all_interview_data = []
    all_biography_data = []
    
    for user_id in args.user_ids:
        # Load comparison files for interview
        comparison_file = Path("logs") / user_id / "evaluations" / "interview_comparisons.csv"
        if comparison_file.exists():
            df = pd.read_csv(comparison_file)
            all_interview_data.append(df)
        
        # Load comparison files for biography
        eval_dir = Path("logs") / user_id / "evaluations"
        if eval_dir.exists():
            bio_dirs = [d for d in eval_dir.glob("biography_*") if d.is_dir()]
            for bio_dir in bio_dirs:
                comparison_file = bio_dir / "biography_comparisons.csv"
                if comparison_file.exists():
                    df = pd.read_csv(comparison_file)
                    all_biography_data.append(df)
    
    # Combine all dataframes
    interview_df = pd.concat(all_interview_data) if all_interview_data else pd.DataFrame()
    biography_df = pd.concat(all_biography_data) if all_biography_data else pd.DataFrame()
    
    # Calculate results from combined data
    interview_results = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    biography_results = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    
    # Process interview data
    for _, row in interview_df.iterrows():
        # Determine which model is baseline and get voting results
        if row['Model A'] == 'ours':
            baseline_model = row['Model B']
            for criterion in ['Smooth Score', 'Flexibility Score', 'Comforting Score']:
                winner_col = f'{criterion} Winner'
                if winner_col in interview_df.columns:
                    winner = row[winner_col]
                    interview_results[baseline_model][criterion][2] += 1
                    if winner == 'A':  # Our model won
                        interview_results[baseline_model][criterion][0] += 1
                    elif winner == 'Tie':  # Tie
                        interview_results[baseline_model][criterion][1] += 1
        else:
            baseline_model = row['Model A']
            for criterion in ['Smooth Score', 'Flexibility Score', 'Comforting Score']:
                winner_col = f'{criterion} Winner'
                if winner_col in interview_df.columns:
                    winner = row[winner_col]
                    interview_results[baseline_model][criterion][2] += 1
                    if winner == 'B':  # Our model won
                        interview_results[baseline_model][criterion][0] += 1
                    elif winner == 'Tie':  # Tie
                        interview_results[baseline_model][criterion][1] += 1
    
    # Process biography data
    for _, row in biography_df.iterrows():
        # Determine which model is baseline and get voting results
        if row['Model A'] == 'ours':
            baseline_model = row['Model B']
            for criterion in ['Insightfulness', 'Narrativity', 'Coherence']:
                winner_col = f'{criterion} Winner'
                if winner_col in biography_df.columns:
                    winner = row[winner_col]
                    biography_results[baseline_model][criterion][2] += 1
                    if winner == 'A':  # Our model won
                        biography_results[baseline_model][criterion][0] += 1
                    elif winner == 'Tie':  # Tie
                        biography_results[baseline_model][criterion][1] += 1
        else:
            baseline_model = row['Model A']
            for criterion in ['Insightfulness', 'Narrativity', 'Coherence']:
                winner_col = f'{criterion} Winner'
                if winner_col in biography_df.columns:
                    winner = row[winner_col]
                    biography_results[baseline_model][criterion][2] += 1
                    if winner == 'B':  # Our model won
                        biography_results[baseline_model][criterion][0] += 1
                    elif winner == 'Tie':  # Tie
                        biography_results[baseline_model][criterion][1] += 1
    
    # Display the aggregated results
    display_results(interview_results, biography_results)

if __name__ == '__main__':
    main() 