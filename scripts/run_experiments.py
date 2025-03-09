#!/usr/bin/env python3
import argparse
from experiment_utils import (
    backup_env_file, 
    restore_env_file, 
    load_env_variables, 
    run_experiment
)

def main():
    parser = argparse.ArgumentParser(
        description="Run experiments with different configurations")
    parser.add_argument("--user_id", required=True, 
                        help="User ID for the experiment")
    parser.add_argument("--timeout", type=int, default=8, 
                        help="Timeout in minutes for each session (default: 8)")
    parser.add_argument("--skip_baseline", action="store_true", 
                        help="Skip baseline experiments")
    args = parser.parse_args()
    
    # Create a backup of the original .env file
    backup_file = backup_env_file()
    
    try:
        # Load environment variables
        load_env_variables()
        
        # Configuration for experiments
        experiments = []
        
        # Always add our work
        experiments.append({"model_name": "gpt-4o", "use_baseline": False})
        
        # Add baselines if not skipped
        if not args.skip_baseline:
            experiments.extend([
                {"model_name": "gpt-4o", "use_baseline": True},
                {"model_name": "gemini-1.5-pro", "use_baseline": True}
            ])
        
        # Run experiments
        for exp in experiments:
            print("\n" + "="*80)
            print(f"Running experiment with model: {exp['model_name']}, baseline: {exp['use_baseline']}")
            print("="*80)
            
            run_experiment(args.user_id, exp["model_name"], exp["use_baseline"], args.timeout)
            
            print(f"Experiment completed for {exp['model_name']}")
        
        print("\nAll experiments completed!")
    
    finally:
        # Restore the original .env file
        restore_env_file(backup_file)

if __name__ == "__main__":
    main() 