#!/usr/bin/env python3
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import pandas as pd
import re

def get_latest_biography_version(eval_dir: Path) -> Optional[int]:
    """Get the latest biography version number from evaluation directory.
    
    Args:
        eval_dir: Path to the evaluations directory
    
    Returns:
        Latest biography version number or None if 
        no biography directories found
    """
    bio_dirs = [d for d in eval_dir.glob("biography_*") if d.is_dir()]
    if not bio_dirs:
        return None
    
    version_numbers = []
    for d in bio_dirs:
        match = re.search(r'biography_(\d+)', str(d))
        if match:
            version_numbers.append(int(match.group(1)))
    
    return max(version_numbers) if version_numbers else None

def load_biography_metrics(user_id: str, bio_version: Optional[int] = None, model_name: Optional[str] = None) -> Optional[Dict[str, float]]:
    """Load biography metrics for a specific user and model.
    
    Args:
        user_id: The user ID to analyze
        bio_version: Optional specific biography version to analyze
        model_name: Optional model name for baseline experiments
        
    Returns:
        Dictionary with completeness and groundedness scores or 
        None if not found
    """
    # Determine the base directory
    if model_name:
        base_dir = Path(f'logs_{model_name}')
    else:
        base_dir = Path('logs')
    
    eval_dir = base_dir / user_id / "evaluations"
    if not eval_dir.exists():
        return None
    
    # Get the biography version to analyze
    version = bio_version if bio_version is not None else get_latest_biography_version(eval_dir)
    if version is None:
        return None
    
    bio_dir = eval_dir / f"biography_{version}"
    if not bio_dir.exists():
        print(f"Warning: Biography version {version} not found for {model_name if model_name else 'our'} model")
        return None
    
    metrics = {}
    
    # Load completeness
    completeness_file = bio_dir / "completeness_summary.csv"
    if completeness_file.exists():
        # Only read the first few lines containing the summary metrics
        df = pd.read_csv(completeness_file, nrows=4)
        coverage = df.loc[df['Metric'] == 'Memory Coverage',
                           'Value'].iloc[0]
        metrics['completeness'] = float(coverage.strip('%'))
    
    # Load groundedness
    groundedness_file = bio_dir / "overall_groundedness.csv"
    if groundedness_file.exists():
        # Only read the header and first data row
        df = pd.read_csv(groundedness_file, nrows=1)
        groundedness = df['Overall Groundedness Score'].iloc[0]
        metrics['groundedness'] = float(groundedness.strip('%'))
    
    return metrics if metrics else None

def analyze_user_metrics(user_id: str, bio_version: Optional[int] = None) -> Tuple[Dict[str, Dict[str, float]], Optional[Dict[str, float]]]:
    """Analyze biography metrics for a single user.
    
    Args:
        user_id: The user ID to analyze
        bio_version: Optional specific biography version to analyze
        
    Returns:
        Tuple of (baseline_metrics, our_metrics)
        baseline_metrics is a dict mapping model names to their metrics
    """
    baseline_metrics = {}
    our_metrics = None
    
    # Get baseline models (directories starting with logs_)
    baseline_models = [d.name[5:] for d in Path('.').glob('logs_*') \
                        if d.is_dir()]
    
    # Load baseline metrics
    for model in baseline_models:
        metrics = load_biography_metrics(user_id, bio_version, model)
        if metrics:
            baseline_metrics[model] = metrics
    
    # Load our metrics
    our_metrics = load_biography_metrics(user_id, bio_version)
    
    return baseline_metrics, our_metrics

def analyze_multiple_users(user_ids: List[str], bio_version: Optional[int] = None) -> Tuple[Dict[str, Dict[str, float]], Optional[Dict[str, float]]]:
    """Analyze biography metrics for multiple users.
    
    Args:
        user_ids: List of user IDs to analyze
        bio_version: Optional specific biography version to analyze
        
    Returns:
        Tuple of (baseline_metrics, our_metrics)
        baseline_metrics is a dict mapping model names to their metrics
    """
    all_baseline_metrics = {}
    all_our_metrics = []
    
    for user_id in user_ids:
        baseline_metrics, our_metrics = analyze_user_metrics(user_id, bio_version)
        
        # Aggregate baseline metrics by model
        for model, metrics in baseline_metrics.items():
            if model not in all_baseline_metrics:
                all_baseline_metrics[model] = defaultdict(list)
            for metric, value in metrics.items():
                all_baseline_metrics[model][metric].append(value)
        
        # Collect our metrics
        if our_metrics:
            all_our_metrics.append(our_metrics)
    
    # Average baseline metrics for each model
    final_baseline_metrics = {
        model: {
            metric: sum(values)/len(values)
            for metric, values in metrics.items()
        }
        for model, metrics in all_baseline_metrics.items()
    }
    
    # Average our metrics
    final_our_metrics = {
        metric: sum(m[metric] for m in all_our_metrics)/len(all_our_metrics)
        for metric in ['completeness', 'groundedness']
    } if all_our_metrics else None
    
    return final_baseline_metrics, final_our_metrics

def display_results(baseline_metrics: Dict[str, Dict[str, float]], 
                   our_metrics: Optional[Dict[str, float]],
                   bio_version: Optional[int] = None) -> None:
    """Display results in a formatted table.
    
    Args:
        baseline_metrics: Dictionary mapping model names to their metrics
        our_metrics: Our method's metrics
        bio_version: Biography version being analyzed
    """
    version_str = f" (Version {bio_version})" if bio_version is not None else " (Latest Version)"
    print(f"\nBiography Quality Metrics{version_str}:")
    print("-" * 75)
    print(f"{'Model':<25} {'Memory Coverage':>20} {'Groundedness':>20}")
    print("-" * 75)
    
    # Print baseline metrics for each model
    for model, metrics in baseline_metrics.items():
        print(f"{model:<25} "
              f"{metrics.get('completeness', 0):>19.2f}% "
              f"{metrics.get('groundedness', 0):>19.2f}%")
    
    # Print our metrics
    if our_metrics:
        print("-" * 75)
        print(f"{'Ours':<25} "
              f"{our_metrics.get('completeness', 0):>19.2f}% "
              f"{our_metrics.get('groundedness', 0):>19.2f}%")
    print("-" * 75)

def main():
    parser = argparse.ArgumentParser(
        description="Analyze biography quality metrics")
    parser.add_argument('--user_ids', nargs='+', required=True,
                      help='One or more user IDs to analyze')
    parser.add_argument('--bio_version', type=int, default=None,
                      help='Specific biography version to analyze (default: latest)')
    args = parser.parse_args()
    
    if len(args.user_ids) == 1:
        baseline_metrics, our_metrics = \
            analyze_user_metrics(args.user_ids[0], args.bio_version)
    else:
        baseline_metrics, our_metrics = \
            analyze_multiple_users(args.user_ids, args.bio_version)
    
    display_results(baseline_metrics, our_metrics, args.bio_version)

if __name__ == '__main__':
    main() 