#!/usr/bin/env python3
import os
import time
import signal
import subprocess
import shutil
from datetime import datetime
import dotenv
from typing import Optional, Dict
import fnmatch
from pathlib import Path

def backup_env_file() -> Optional[str]:
    """Create a backup of the original .env file
    
    Returns:
        Optional[str]: Path to the backup file if created, None otherwise
    """
    if os.path.exists('.env'):
        backup_file = f'.env.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        shutil.copy2('.env', backup_file)
        print(f"Created backup of .env file: {backup_file}")
        return backup_file
    return None

def restore_env_file(backup_file: Optional[str]) -> None:
    """Restore the original .env file from backup
    
    Args:
        backup_file (Optional[str]): Path to the backup file to restore from
    """
    if backup_file and os.path.exists(backup_file):
        shutil.copy2(backup_file, '.env')
        print(f"Restored original .env file from backup: {backup_file}")

def load_env_variables() -> None:
    """Load environment variables from .env file"""
    dotenv.load_dotenv()

def update_env_file(model_name: str, use_baseline: bool, logs_dir: Optional[str] = None, data_dir: Optional[str] = None) -> None:
    """Update the .env file with the specified configuration
    
    Args:
        model_name (str): Name of the model to use
        use_baseline (bool): Whether to use baseline prompt
        logs_dir (Optional[str]): Directory for logs
        data_dir (Optional[str]): Directory for data
    """
    # Load current env variables
    env_vars: Dict[str, str] = {}
    with open('.env', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
    
    # Update values
    env_vars["EVAL_MODE"] = "true"
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

def wait_for_completion(process: subprocess.Popen, timeout_minutes: float = 1) -> bool:
    """Wait for a process to complete with a timeout.
    
    Args:
        process (subprocess.Popen): Process to wait for
        timeout_minutes (float): Timeout in minutes
    
    Returns:
        bool: True if process completed within timeout, False otherwise
    """
    try:
        process.wait(timeout=timeout_minutes * 60)
        return True
    except subprocess.TimeoutExpired:
        print("Process is taking longer than expected...")
        return False

def run_command_with_timeout(command: str, timeout_minutes: int) -> None:
    """Run a command with a timeout and end it properly with a keyboard interrupt
    
    Args:
        command (str): Command to run
        timeout_minutes (int): Timeout in minutes
    """
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
        
        print("Waiting for session to finish gracefully...")
        if not wait_for_completion(process, timeout_minutes=10):
            print("Session is taking too long to finish. Attempting graceful termination...")
            process.terminate()
            if not wait_for_completion(process, timeout_minutes=5):
                print("Process still not terminated. Force killing...")
                process.kill()
                process.wait()
    
    except KeyboardInterrupt:
        # Allow manual termination
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"Process terminated by user")
        if not wait_for_completion(process, timeout_minutes=10):
            print("Session is taking too long to finish. Attempting graceful termination...")
            process.terminate()
            if not wait_for_completion(process, timeout_minutes=5):
                print("Process still not terminated. Force killing...")
                process.kill()
                process.wait()
    
    # Give some time for final cleanup
    time.sleep(5)

def run_evaluation(user_id: str, eval_type: str) -> bool:
    """Run evaluation script
    
    Args:
        user_id (str): User ID for the evaluation
        eval_type (str): Type of evaluation to run
    
    Returns:
        bool: True if evaluation succeeded, False otherwise
    """
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

def clear_user_data(user_id: str, model_name: Optional[str] = None, clear_all: bool = False) -> None:
    """Clear existing user data.
    
    Args:
        user_id: User ID to clear data for
        model_name: If provided, only clear data for this specific model
        clear_all: If True, clear data for all models (overrides model_name)
    """
    if clear_all:
        # Clear main directories
        logs_dir = "logs"
        data_dir = "data"
        print(f"Clearing main directories: {logs_dir} and {data_dir}")
        
        # Clear logs directory
        user_logs_dir = Path(logs_dir) / user_id
        if user_logs_dir.exists():
            print(f"Removing logs directory: {user_logs_dir}")
            shutil.rmtree(user_logs_dir)
        
        # Clear data directory
        user_data_dir = Path(data_dir) / user_id
        if user_data_dir.exists():
            print(f"Removing data directory: {user_data_dir}")
            shutil.rmtree(user_data_dir)
        
        # Find and clear all model-specific directories
        for dir_name in os.listdir('.'):
            if dir_name.startswith('logs_'):
                model_logs_dir = Path(dir_name) / user_id
                if model_logs_dir.exists():
                    print(f"Removing model logs directory: {model_logs_dir}")
                    shutil.rmtree(model_logs_dir)
            
            if dir_name.startswith('data_'):
                model_data_dir = Path(dir_name) / user_id
                if model_data_dir.exists():
                    print(f"Removing model data directory: {model_data_dir}")
                    shutil.rmtree(model_data_dir)
        
        print(f"Cleared all data for user: {user_id}")
        return
    
    # Determine which directories to clear based on model_name
    if model_name:
        # For baseline models, clear model-specific directories
        logs_dir = f"logs_{model_name.replace('-', '_')}"
        data_dir = f"data_{model_name.replace('-', '_')}"
        print(f"Clearing model-specific directories: {logs_dir} and {data_dir}")
    else:
        # For our model, clear main logs/data directories
        logs_dir = "logs"
        data_dir = "data"
        print(f"Clearing main directories: {logs_dir} and {data_dir}")
    
    # Clear logs directory
    user_logs_dir = Path(logs_dir) / user_id
    if user_logs_dir.exists():
        print(f"Removing logs directory: {user_logs_dir}")
        shutil.rmtree(user_logs_dir)
    
    # Clear data directory
    user_data_dir = Path(data_dir) / user_id
    if user_data_dir.exists():
        print(f"Removing data directory: {user_data_dir}")
        shutil.rmtree(user_data_dir)

def run_experiment(user_id: str, model_name: str, use_baseline: bool, timeout_minutes: int) -> str:
    """Run a single experiment with the specified configuration
    
    Args:
        user_id (str): User ID for the experiment
        model_name (str): Name of the model to use
        use_baseline (bool): Whether to use baseline prompt
        timeout_minutes (int): Timeout in minutes for the session
        restart (bool): Whether to clear existing user data before running
                       (Note: This is typically handled by the calling script now)
    
    Returns:
        str: The experiment ID
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    experiment_id = f"{model_name.replace('-', '_')}_baseline_" \
                   f"{str(use_baseline).lower()}_{timestamp}"
    
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting experiment: {experiment_id}")
    
    # Set up environment variables and directories
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
    eval_results: Dict[str, str] = {}
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
    
    # Add a clear separator between experiments
    print("\n" + "="*80 + "\n")
    
    return experiment_id 