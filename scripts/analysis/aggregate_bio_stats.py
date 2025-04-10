#!/usr/bin/env python3
"""
Biography Statistics Aggregator

This script reads the bio_stats.csv file and aggregates statistics by baseline
system and user group (treatment vs control). It generates a new CSV file with
the aggregated results.

Usage:
    python aggregate_bio_stats.py [--input INPUT] [--output OUTPUT]

Where:
    --input: Path to bio_stats.csv (default: logs_bio/bio_stats.csv)
    --output: Path to output aggregated statistics (default: logs_bio/aggregated_stats.csv)
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np


def load_bio_stats(input_file: str) -> pd.DataFrame:
    """
    Load biography statistics from CSV file into a pandas DataFrame.
    
    Args:
        input_file: Path to the bio_stats.csv file
        
    Returns:
        DataFrame containing the statistics
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Statistics file not found: {input_file}")
        
    # Read CSV into pandas DataFrame
    df = pd.read_csv(input_file)
    
    # Check if required columns exist
    required_columns = ["user_id", "baseline", "group"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(f"Required columns missing from CSV: {', '.join(missing_columns)}")
        
    return df


def aggregate_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate statistics by baseline and group.
    
    Args:
        df: DataFrame with biography statistics
        
    Returns:
        DataFrame with aggregated statistics, numeric values rounded to 2 decimal places
    """
    # Ensure baseline and group are treated as categories
    df["baseline"] = df["baseline"].astype(str)
    df["group"] = df["group"].astype(str)
    
    # Define key metrics to aggregate
    key_metrics = [
        "word_count",
        "character_count",
        "total_sections",
        "total_memory_references",
        "avg_words_per_section"
    ]
    
    # Create aggregation dictionary for key metrics
    agg_dict = {
        col: ["mean", "median", "std"] 
        for col in key_metrics
    }
    
    # Group by baseline and group, then aggregate
    grouped_df = df.groupby(["baseline", "group"]).agg(agg_dict)
    
    # Flatten the multi-index columns
    grouped_df.columns = [f"{col}_{stat}" for col, stat in grouped_df.columns]
    
    # Reset index to make baseline and group regular columns
    grouped_df = grouped_df.reset_index()
    
    # Round numeric columns to 2 decimal places
    for col in grouped_df.columns:
        if grouped_df[col].dtype in [np.float64, np.float32]:
            grouped_df[col] = grouped_df[col].round(2)
    
    return grouped_df


def save_aggregated_stats(df: pd.DataFrame, output_file: str) -> None:
    """
    Save aggregated statistics to CSV file.
    
    Args:
        df: DataFrame with aggregated statistics
        output_file: Path to save the aggregated statistics
    """
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Save to CSV
    df.to_csv(output_file, index=False)
    print(f"Aggregated statistics saved to {output_file}")


def generate_summary_statistics(df: pd.DataFrame, output_file: str) -> None:
    """
    Generate a summary statistics file with key metrics.
    
    Args:
        df: Original DataFrame with biography statistics
        output_file: Path to save the summary statistics
    """
    summary_file = output_file.replace(".csv", "_summary.csv")
    
    # Prepare summary data
    summary_data = []
    
    # Get unique combinations of baseline and group
    combinations = df[["baseline", "group"]].drop_duplicates().values
    
    for baseline, group in combinations:
        subset = df[(df["baseline"] == baseline) & (df["group"] == group)]
        
        # Calculate key statistics
        stats = {
            "baseline": baseline,
            "group": group,
            "user_count": len(subset),
            "avg_word_count": round(subset["word_count"].mean(), 2),
            "avg_sections": round(subset["total_sections"].mean(), 2),
            "avg_memory_references": round(subset["total_memory_references"].mean(), 2),
            "avg_words_per_section": round(subset["avg_words_per_section"].mean(), 2)
        }
        
        summary_data.append(stats)
    
    # Add overall statistics
    overall_stats = {
        "baseline": np.nan,
        "group": np.nan,
        "user_count": len(df),
        "avg_word_count": round(df["word_count"].mean(), 2),
        "avg_sections": round(df["total_sections"].mean(), 2),
        "avg_memory_references": round(df["total_memory_references"].mean(), 2),
        "avg_words_per_section": round(df["avg_words_per_section"].mean(), 2)
    }
    summary_data.append(overall_stats)
    
    # Save summary to CSV
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(summary_file, index=False)
    print(f"Summary statistics saved to {summary_file}")


def main():
    parser = argparse.ArgumentParser(description="Aggregate biography statistics by baseline and group.")
    parser.add_argument("--input", "-i", default="logs_bio/bio_stats.csv", 
                        help="Path to bio_stats.csv (default: logs_bio/bio_stats.csv)")
    parser.add_argument("--output", "-o", default="logs_bio/aggregated_stats.csv",
                        help="Path to output aggregated statistics (default: logs_bio/aggregated_stats.csv)")
    
    args = parser.parse_args()
    
    try:
        # Load statistics
        df = load_bio_stats(args.input)
        print(f"Loaded statistics for {len(df)} users")
        
        # Aggregate statistics
        aggregated_df = aggregate_statistics(df)
        
        # Save aggregated statistics
        save_aggregated_stats(aggregated_df, args.output)
        
        # Generate summary statistics
        generate_summary_statistics(df, args.output)
        
        print("Aggregation completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 