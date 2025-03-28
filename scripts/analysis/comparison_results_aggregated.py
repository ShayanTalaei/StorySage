#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

import argparse
import pandas as pd
from typing import Dict, Tuple, List
from collections import defaultdict

def load_interview_comparisons_by_session(user_id: str) -> Dict[str, Dict[str, Tuple[int, int, int]]]:
    """Load interview comparison results for a user, aggregating by session first.
    
    Args:
        user_id: The user ID to analyze
        
    Returns:
        Dictionary mapping baseline models to their metrics (wins, ties, total)
    """
    # First aggregate by session
    session_results = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(
                lambda: [0, 0, 0])))
    
    # Load from the main logs directory
    comparison_file = Path("logs") / user_id / "evaluations" / "interview_comparisons.csv"
    
    if comparison_file.exists():
        df = pd.read_csv(comparison_file)
        
        # Group by session ID
        for session_id, session_df in df.groupby('Session ID'):
            for _, row in session_df.iterrows():
                # Determine which model is baseline and get voting results
                if row['Model A'] == 'ours':
                    baseline_model = row['Model B']
                    for criterion in ['Smooth Score', 'Flexibility Score', 
                                      'Comforting Score']:
                        winner_col = f'{criterion} Winner'
                        if winner_col in df.columns:
                            winner = row[winner_col]
                            session_results[session_id][baseline_model][criterion][2] += 1
                            if winner == 'A':  # Our model won
                                session_results[session_id][baseline_model][criterion][0] += 1
                            elif winner == 'Tie':  # Tie
                                session_results[session_id][baseline_model][criterion][1] += 1
                else:
                    baseline_model = row['Model A']
                    for criterion in ['Smooth Score', 'Flexibility Score', 'Comforting Score']:
                        winner_col = f'{criterion} Winner'
                        if winner_col in df.columns:
                            winner = row[winner_col]
                            session_results[session_id][baseline_model][criterion][2] += 1
                            if winner == 'B':  # Our model won
                                session_results[session_id][baseline_model][criterion][0] += 1
                            elif winner == 'Tie':  # Tie
                                session_results[session_id][baseline_model][criterion][1] += 1
    
    # Now aggregate across sessions
    final_results = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    session_count = defaultdict(int)
    
    for session_id, model_results in session_results.items():
        for model, criterion_results in model_results.items():
            session_count[model] += 1
            for criterion, (wins, ties, total) in criterion_results.items():
                final_results[model][criterion][0] += wins
                final_results[model][criterion][1] += ties
                final_results[model][criterion][2] += total
    
    # Average the results by number of sessions
    for model in final_results:
        for criterion in final_results[model]:
            for i in range(3):
                final_results[model][criterion][i] /= session_count[model]
            # Round to nearest integer after averaging
            final_results[model][criterion] = [round(x) for x in final_results[model][criterion]]
    
    return final_results

def load_biography_comparisons_by_version(user_id: str) -> Dict[str, Dict[str, Tuple[int, int, int]]]:
    """Load biography comparison results for a user, aggregating by version first.
    
    Args:
        user_id: The user ID to analyze
        
    Returns:
        Dictionary mapping baseline models to their metrics (wins, ties, total)
    """
    # First aggregate by version
    version_results = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0, 0, 0])))
    
    # Find all biography version directories
    eval_dir = Path("logs") / user_id / "evaluations"
    if not eval_dir.exists():
        return defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    
    bio_dirs = [d for d in eval_dir.glob("biography_*") if d.is_dir()]
    
    for bio_dir in bio_dirs:
        version = int(bio_dir.name.split('_')[1])
        comparison_file = bio_dir / "biography_comparisons.csv"
        
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
                            version_results[version][baseline_model][criterion][2] += 1
                            if winner == 'A':  # Our model won
                                version_results[version][baseline_model][criterion][0] += 1
                            elif winner == 'Tie':  # Tie
                                version_results[version][baseline_model][criterion][1] += 1
                else:
                    baseline_model = row['Model A']
                    for criterion in ['Insightfulness', 'Narrativity', 'Coherence']:
                        winner_col = f'{criterion} Winner'
                        if winner_col in df.columns:
                            winner = row[winner_col]
                            version_results[version][baseline_model][criterion][2] += 1
                            if winner == 'B':  # Our model won
                                version_results[version][baseline_model][criterion][0] += 1
                            elif winner == 'Tie':  # Tie
                                version_results[version][baseline_model][criterion][1] += 1
    
    # Now aggregate across versions
    final_results = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    version_count = defaultdict(int)
    
    for version, model_results in version_results.items():
        for model, criterion_results in model_results.items():
            version_count[model] += 1
            for criterion, (wins, ties, total) in criterion_results.items():
                final_results[model][criterion][0] += wins
                final_results[model][criterion][1] += ties
                final_results[model][criterion][2] += total
    
    # Average the results by number of versions
    for model in final_results:
        for criterion in final_results[model]:
            for i in range(3):
                final_results[model][criterion][i] /= version_count[model]
            # Round to nearest integer after averaging
            final_results[model][criterion] = [round(x) for x in final_results[model][criterion]]
    
    return final_results

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
        description="Display comparison results aggregated by session/version")
    parser.add_argument('--user_ids', nargs='+', required=True,
                      help='One or more user IDs to analyze')
    args = parser.parse_args()
    
    # Aggregate results across all users
    all_interview_results = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    all_biography_results = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    
    for user_id in args.user_ids:
        # Load interview comparisons (aggregated by session)
        interview_results = load_interview_comparisons_by_session(user_id)
        
        # Load biography comparisons (aggregated by version)
        biography_results = load_biography_comparisons_by_version(user_id)
        
        # Aggregate results across users
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