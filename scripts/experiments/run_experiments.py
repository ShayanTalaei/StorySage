#!/usr/bin/env python3
import argparse
from experiment_utils import (
    backup_env_file, 
    restore_env_file, 
    load_env_variables, 
    run_experiment,
)
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(
        description="Run experiments with different configurations")
    parser.add_argument("--user_id", required=True, 
                        help="User ID for the experiment")
    parser.add_argument("--max_turns", type=int, required=True, 
                        help="Maximum number of turns for each session")
    parser.add_argument("--restart", action="store_true",
                        help="Clear existing user data before experiments",
                        default=False)
    args = parser.parse_args()
    
    # Create a backup of the original .env file
    backup_file = backup_env_file()
    
    try:
        # Load environment variables
        load_env_variables()
        
        # If restart is requested, clear all user data upfront
        if args.restart:
            print("\nClearing all existing user data...")
        
        # Configuration for experiments
        experiments = [
            {"model_name": "gpt-4o", "use_baseline": False},
            {"model_name": "gpt-4o", "use_baseline": True},
            {"model_name": "gemini-1.5-pro", "use_baseline": True},
        ]
        
        # Create a summary file
        summary_file = \
            f"experiment_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(summary_file, 'w') as f:
            f.write(f"Experiment Summary - "
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"User ID: {args.user_id}\n")
            f.write(f"Max Turns: {args.max_turns}\n")
            f.write(f"Restart: {args.restart}\n\n")
        
        # Run experiments
        for i, exp in enumerate(experiments, 1):
            print("\n" + "="*80)
            print(f"Running experiment {i} of {len(experiments)}")
            print(f"Model: {exp['model_name']}, Baseline: {exp['use_baseline']}")
            print("="*80)
            
            experiment_name = run_experiment(
                user_id=args.user_id,
                model_name=exp["model_name"],
                use_baseline=exp["use_baseline"],
                max_turns=args.max_turns,
                restart=args.restart
            )
            
            # Add to summary
            with open(summary_file, 'a') as f:
                f.write(f"\nExperiment: {experiment_name}\n")
                f.write(f"Model: {exp['model_name']}\n")
                f.write(f"Baseline: {exp['use_baseline']}\n")
                f.write(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-"*40 + "\n")
        
        print(f"\nAll experiments completed! Summary saved to {summary_file}")
    
    finally:
        # Restore the original .env file
        restore_env_file(backup_file)

if __name__ == "__main__":
    main() 