#!/usr/bin/env python3
import argparse
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

def load_question_similarity_data(user_id: str, model_name: Optional[str] = None) -> pd.DataFrame:
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
    
    # Check if the directory exists
    if not logs_dir.exists():
        print(f"Logs directory not found: {logs_dir}")
        return pd.DataFrame()
    
    # Find the question similarity file
    similarity_file = logs_dir / user_id / "evaluations" / "question_similarity.csv"
    
    if not similarity_file.exists():
        print(f"Question similarity file not found: {similarity_file}")
        return pd.DataFrame()
    
    # Load the data
    try:
        df = pd.read_csv(similarity_file)
        # Add model information
        df['model'] = 'ours' if model_name is None else model_name
        return df
    except Exception as e:
        print(f"Error loading question similarity data: {e}")
        return pd.DataFrame()

def analyze_repetition_rate(df: pd.DataFrame) -> Dict[str, float]:
    """Analyze question repetition rate from a DataFrame.
    
    Args:
        df: DataFrame with question similarity data
        
    Returns:
        Dictionary with repetition metrics
    """
    if df.empty:
        return {
            'total_questions': 0,
            'duplicate_questions': 0,
            'repetition_rate': 0.0
        }
    
    # Count total questions and duplicates
    total_questions = len(df)
    
    # Handle string "True"/"False" values in "Is Duplicate" column
    if 'Is Duplicate' in df.columns:
        # Convert string "True"/"False" to boolean values
        duplicate_questions = df['Is Duplicate'].apply(
            lambda x: x == "True" or x is True).sum()
    else:
        duplicate_questions = 0
    
    # Calculate repetition rate
    repetition_rate = duplicate_questions / total_questions if total_questions > 0 else 0
    
    return {
        'total_questions': total_questions,
        'duplicate_questions': duplicate_questions,
        'repetition_rate': repetition_rate
    }

def analyze_user_repetition(user_id: str) -> Dict[str, Dict[str, float]]:
    """Analyze question repetition for a single user across all models.
    
    Args:
        user_id: The user ID to analyze
        
    Returns:
        Dictionary mapping models to their repetition metrics
    """
    results = {}
    
    # Analyze our model
    our_df = load_question_similarity_data(user_id)
    if not our_df.empty:
        results['ours'] = analyze_repetition_rate(our_df)
    
    # Find baseline model directories
    baseline_models = []
    for dir_name in Path('.').glob('logs_*'):
        if dir_name.is_dir():
            model_name = dir_name.name[5:]  # Remove 'logs_' prefix
            baseline_models.append(model_name)
    
    # Analyze baseline models
    for model_name in baseline_models:
        baseline_df = load_question_similarity_data(user_id, model_name)
        if not baseline_df.empty:
            results[model_name] = analyze_repetition_rate(baseline_df)
    
    return results

def analyze_multiple_users(user_ids: List[str]) -> Dict[str, Dict[str, float]]:
    """Analyze question repetition for multiple users and aggregate results.
    
    Args:
        user_ids: List of user IDs to analyze
        
    Returns:
        Dictionary mapping models to their aggregated repetition metrics
    """
    # Initialize aggregated results
    aggregated_results = defaultdict(lambda: {
        'total_questions': 0,
        'duplicate_questions': 0,
        'repetition_rate': 0.0,
        'user_count': 0
    })
    
    # Analyze each user
    for user_id in user_ids:
        user_results = analyze_user_repetition(user_id)
        
        # Aggregate results for each model
        for model, metrics in user_results.items():
            aggregated_results[model]['total_questions'] += metrics['total_questions']
            aggregated_results[model]['duplicate_questions'] += \
                metrics['duplicate_questions']
            aggregated_results[model]['user_count'] += 1
    
    # Calculate average repetition rates
    for model in aggregated_results:
        total = aggregated_results[model]['total_questions']
        duplicates = aggregated_results[model]['duplicate_questions']
        aggregated_results[model]['repetition_rate'] = \
              duplicates / total if total > 0 else 0
    
    return dict(aggregated_results)

def display_results(results: Dict[str, Dict[str, float]]) -> None:
    """Display repetition analysis results in a formatted table.
    
    Args:
        results: Dictionary mapping models to their repetition metrics
    """
    print("\n" + "=" * 80)
    print("QUESTION REPETITION ANALYSIS")
    print("=" * 80)
    
    # Print header
    print(f"{'Model':20} | {'Total Questions':^15} | {'Duplicates':^15} | {'Repetition Rate':^15}")
    print("-" * 80)
    
    # Print results for each model
    for model in sorted(results.keys()):
        metrics = results[model]
        total = metrics['total_questions']
        duplicates = metrics['duplicate_questions']
        rate = metrics['repetition_rate']
        
        print(f"{model:20} | {total:^15} | {duplicates:^15} | {rate:.2%}")
    
    print("=" * 80)

def main():
    parser = argparse.ArgumentParser(
        description="Analyze question repetition rates across different models")
    parser.add_argument('--user_ids', nargs='+', required=True,
                      help='One or more user IDs to analyze')
    args = parser.parse_args()
    
    # Analyze based on number of users
    if len(args.user_ids) == 1:
        # Single user analysis
        user_id = args.user_ids[0]
        print(f"Analyzing question repetition for user: {user_id}")
        results = analyze_user_repetition(user_id)
    else:
        # Multiple user analysis
        print(f"Analyzing question repetition for {len(args.user_ids)} users")
        results = analyze_multiple_users(args.user_ids)
    
    # Display results
    display_results(results)

if __name__ == "__main__":
    main() 