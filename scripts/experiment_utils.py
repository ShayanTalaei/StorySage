#!/usr/bin/env python3
import os
import time
import signal
import subprocess
import shutil
from datetime import datetime
import dotenv

def backup_env_file():
    """Create a backup of the original .env file"""
    if os.path.exists('.env'):
        backup_file = f'.env.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        shutil.copy2('.env', backup_file)
        print(f"Created backup of .env file: {backup_file}")
        return backup_file
    return None

def restore_env_file(backup_file):
    """Restore the original .env file from backup"""
    if backup_file and os.path.exists(backup_file):
        shutil.copy2(backup_file, '.env')
        print(f"Restored original .env file from backup: {backup_file}")

def load_env_variables():
    """Load environment variables from .env file"""
    dotenv.load_dotenv()

def update_env_file(model_name, use_baseline, logs_dir=None, data_dir=None):
    """Update the .env file with the specified configuration"""
    # Load current env variables
    env_vars = {}
    with open('.env', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
    
    # Update values
    env_vars['MODEL_NAME'] = f'"{model_name}"'
    env_vars['USE_BASELINE_PROMPT'] = f'"{str(use_baseline).lower()}"'
    
    if logs_dir:
        env_vars['LOGS_DIR'] = f'"{logs_dir}"'
    if data_dir:
        env_vars['DATA_DIR'] = f'"{data_dir}"'
    
    # Write back to .env file
    with open('.env', 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    print(f"Updated .env file with MODEL_NAME={model_name}, "
          f"USE_BASELINE_PROMPT={str(use_baseline).lower()}")
    if logs_dir:
        print(f"Updated LOGS_DIR={logs_dir}")
    if data_dir:
        print(f"Updated DATA_DIR={data_dir}")

def run_command_with_timeout(command, timeout_minutes):
    """Run a command with a timeout and end it properly with a keyboard interrupt"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
          f"Running command: {command}")
    print(f"Session will run for {timeout_minutes} minutes...")
    
    # Start the process
    process = subprocess.Popen(command, shell=True)
    
    try:
        # Wait for the specified timeout
        time.sleep(timeout_minutes * 60)
        
        # After timeout, send a keyboard interrupt (SIGINT) to properly end the session
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"Sending keyboard interrupt to end session...")
        
        # On Unix/Linux/Mac, we can send SIGINT
        if os.name == 'posix':
            os.kill(process.pid, signal.SIGINT)
        else:
            # On Windows, we need a different approach
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.GenerateConsoleCtrlEvent(0, 0)  # CTRL_C_EVENT
        
        # Wait for the process to finish gracefully
        print("Waiting for session to finish gracefully...")
        try:
            process.wait(timeout=60)  # Wait up to 60 seconds for graceful shutdown
        except subprocess.TimeoutExpired:
            print("Session is taking too long to finish. Forcing termination...")
            process.terminate()
            process.wait(timeout=10)
    
    except KeyboardInterrupt:
        # Allow manual termination
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"Process terminated by user")
        # Don't kill the process, let it handle the KeyboardInterrupt
        try:
            process.wait(timeout=60)  # Wait up to 60 seconds for graceful shutdown
        except subprocess.TimeoutExpired:
            print("Session is taking too long to finish. Forcing termination...")
            process.terminate()
            process.wait(timeout=10)
    
    # Give some time for the process to clean up
    time.sleep(5)

def run_evaluation(user_id, eval_type):
    """Run evaluation script"""
    command = f"python evaluations/{eval_type}.py --user_id {user_id}"
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
          f"Running evaluation: {command}")
    
    # Run the evaluation and capture output
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    # Print the output
    if result.stdout:
        print("Evaluation output:")
        print(result.stdout)
    
    if result.stderr:
        print("Evaluation errors:")
        print(result.stderr)
    
    return result.returncode == 0

def run_experiment(user_id, model_name, use_baseline, timeout_minutes=10):
    """Run a single experiment with the specified configuration"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    experiment_id = f"{model_name.replace('-', '_')}_baseline_{str(use_baseline).lower()}_{timestamp}"
    
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting experiment: {experiment_id}")
    
    # Set up environment variables
    if use_baseline:
        logs_dir = f"logs_{model_name.replace('-', '_')}"
        data_dir = f"data_{model_name.replace('-', '_')}"
        update_env_file(model_name, use_baseline, logs_dir, data_dir)
    else:
        logs_dir = "logs"
        data_dir = "data"
        update_env_file(model_name, use_baseline)
    
    # Create directories if they don't exist
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    
    # Run the interview session
    command = f"python src/main.py --mode terminal --user_id {user_id} --user_agent"
    run_command_with_timeout(command, timeout_minutes)
    
    # Run evaluations
    eval_results = {}
    for eval_type in ["biography_completeness", "biography_groundedness"]:
        success = run_evaluation(user_id, eval_type)
        eval_results[eval_type] = "Success" if success else "Failed"
    
    # Log experiment results
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Experiment completed: {experiment_id}")
    print(f"Model: {model_name}")
    print(f"Baseline: {use_baseline}")
    print(f"User ID: {user_id}")
    print(f"Logs directory: {logs_dir}")
    print(f"Data directory: {data_dir}")
    print("Evaluation results:")
    for eval_type, result in eval_results.items():
        print(f"  - {eval_type}: {result}") 