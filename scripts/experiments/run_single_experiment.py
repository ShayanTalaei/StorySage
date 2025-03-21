#!/usr/bin/env python3
import argparse
from experiment_utils import (
    backup_env_file, 
    restore_env_file, 
    load_env_variables, 
    run_experiment,
)

def main():
    parser = argparse.ArgumentParser(
        description="Run a single experiment with a specific configuration")
    parser.add_argument("--user_id", required=True, 
                        help="User ID for the experiment")
    parser.add_argument("--model", default="gpt-4o", 
                        help="Model to use (default: gpt-4o)")
    parser.add_argument("--baseline", action="store_true", 
                        help="Use baseline prompt")
    parser.add_argument("--timeout", type=int, default=7, 
                        help="Timeout in minutes for the session")
    parser.add_argument("--restart", action="store_true",
                        help="Clear existing user data before running",
                        default=False)
    args = parser.parse_args()
    
    # Create a backup of the original .env file
    backup_file = backup_env_file()
    
    try:
        # Load environment variables
        load_env_variables()
        
        # Run the experiment
        print("\n" + "="*80)
        print(f"Running experiment with model: {args.model}, "
              f"baseline: {args.baseline}")
        print("="*80)
        
        run_experiment(args.user_id, 
                      args.model, 
                      args.baseline, 
                      args.timeout,
                      args.restart)
        
        print("\nExperiment completed!")
    
    finally:
        # Restore the original .env file
        restore_env_file(backup_file)

if __name__ == "__main__":
    main() 