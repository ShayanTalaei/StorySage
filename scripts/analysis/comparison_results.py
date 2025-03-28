#!/usr/bin/env python3
import argparse
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

def load_interview_comparisons(user_id: str, session_id: Optional[int] = None) -> Dict[str, Dict[str, Tuple[int, int, int]]]:
    """Load interview comparison results for a user.
    
    Args:
        user_id: The user ID to analyze
        session_id: Optional specific session ID to analyze
        
    Returns:
        Dictionary mapping baseline models to their metrics (wins, ties, total)
    """
    # Results: [wins, ties, total]
    results = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    
    # Load from the main logs directory
    comparison_file = Path("logs") / user_id / "evaluations" / \
        "interview_comparisons.csv"
    
    if comparison_file.exists():
        df = pd.read_csv(comparison_file)
        
        # Filter by session ID if specified
        if session_id is not None:
            df = df[df['Session ID'] == session_id]
        
        for _, row in df.iterrows():
            # Determine which model is baseline and get voting results
            if row['Model A'] == 'ours':
                baseline_model = row['Model B']
                for criterion in ['Smooth Score', 'Flexibility Score', 
                                'Quality Score', 'Comforting Score']:
                    winner_col = f'{criterion} Winner'
                    if winner_col in df.columns:
                        winner = row[winner_col]
                        results[baseline_model][criterion][2] += 1
                        if winner == 'A':  # Our model won
                            results[baseline_model][criterion][0] += 1
                        elif winner == 'Tie':  # Tie
                            results[baseline_model][criterion][1] += 1
            else:
                baseline_model = row['Model A']
                for criterion in ['Smooth Score', 'Flexibility Score', 
                                'Quality Score', 'Comforting Score']:
                    winner_col = f'{criterion} Winner'
                    if winner_col in df.columns:
                        winner = row[winner_col]
                        results[baseline_model][criterion][2] += 1
                        if winner == 'B':  # Our model won
                            results[baseline_model][criterion][0] += 1
                        elif winner == 'Tie':  # Tie
                            results[baseline_model][criterion][1] += 1
    
    return results

def load_biography_comparisons(user_id: str, biography_version: Optional[int] = None) -> Dict[str, Dict[str, Tuple[int, int, int]]]:
    """Load biography comparison results for a user.
    
    Args:
        user_id: The user ID to analyze
        biography_version: Optional specific biography version to analyze
        
    Returns:
        Dictionary mapping baseline models to their metrics (wins, ties, total)
    """
    # Results: [wins, ties, total]
    results = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    
    # Find the biography version directory
    eval_dir = Path("logs") / user_id / "evaluations"
    
    if not eval_dir.exists():
        return results
    
    # Use specified version or find latest
    if biography_version is not None:
        bio_dir = eval_dir / f"biography_{biography_version}"
        if not bio_dir.exists() or not bio_dir.is_dir():
            print(f"Warning: Biography version {biography_version} not found for user {user_id}")
            return results
    else:
        bio_dirs = [d for d in eval_dir.glob("biography_*") if d.is_dir()]
        if not bio_dirs:
            return results
        bio_dir = max(bio_dirs, key=lambda d: int(d.name.split('_')[1]))
    
    # Load comparison results
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
                        results[baseline_model][criterion][2] += 1
                        if winner == 'A':  # Our model won
                            results[baseline_model][criterion][0] += 1
                        elif winner == 'Tie':  # Tie
                            results[baseline_model][criterion][1] += 1
            else:
                baseline_model = row['Model A']
                for criterion in ['Insightfulness', 'Narrativity', 'Coherence']:
                    winner_col = f'{criterion} Winner'
                    if winner_col in df.columns:
                        winner = row[winner_col]
                        results[baseline_model][criterion][2] += 1  # total
                        if winner == 'B':  # Our model won
                            results[baseline_model][criterion][0] += 1  # wins
                        elif winner == 'Tie':  # Tie
                            results[baseline_model][criterion][1] += 1  # ties
    
    return results

def format_table_cell(wins: int, ties: int, total: int) -> str:
    """Format a table cell with win rate and loss rate as percentages.
    
    Args:
        wins: Number of wins
        ties: Number of ties
        total: Total number of comparisons
        
    Returns:
        Formatted string with win rate and loss rate as percentages
    """
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
        subheader += f" {'W':^7}{'L':^7} |"
    print(subheader)
    
    # Print separator
    print("-" * total_width)
    
    # Rest of the display logic remains the same, just using wider columns
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
        description="Display comparison results in a formatted table")
    parser.add_argument('--user_ids', nargs='+', required=True,
                      help='One or more user IDs to analyze')
    parser.add_argument('--biography_version', type=int,
                      help='Specific biography version to analyze')
    parser.add_argument('--session_id', type=int,
                      help='Specific session ID to analyze for interviews')
    args = parser.parse_args()
    
    # Aggregate results across all users
    all_interview_results = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    all_biography_results = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    
    for user_id in args.user_ids:
        # Load interview comparisons
        interview_results = load_interview_comparisons(user_id, args.session_id)
        
        # Load biography comparisons
        biography_results = load_biography_comparisons(user_id, 
                                                       args.biography_version)
        
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