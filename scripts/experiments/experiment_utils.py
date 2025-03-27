#!/usr/bin/env python3
import os
import time
import signal
import subprocess
import shutil
from datetime import datetime
import dotenv
from typing import Optional, Dict

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
    """Restore the original .env file from backup and delete the backup file.
    
    Args:
        backup_file: Path to the backup file to restore from
    """
    if backup_file and os.path.exists(backup_file):
        try:
            # Restore original .env
            shutil.copy2(backup_file, '.env')
            print(f"Restored original .env file from {backup_file}")
            
            # Delete backup file
            os.remove(backup_file)
            print(f"Deleted backup file: {backup_file}")
        except Exception as e:
            print(f"Error while restoring/cleaning up env file: {e}")

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
        timeout_minutes (int): Timeout in minutes (as backup)
    """
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
          f"Running command: {command}")
    
    # Start the process in its own process group
    process = subprocess.Popen(command, shell=True, preexec_fn=os.setsid)
    
    try:
        # Check process status every second
        elapsed_time = 0
        while elapsed_time < timeout_minutes * 60:  # Convert to seconds
            # Check if process has completed naturally
            if process.poll() is not None:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                      f"Process completed naturally")
                return
            
            time.sleep(1)
            elapsed_time += 1
        
        # If we reach here, timeout occurred
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"Timeout reached. Sending keyboard interrupt to end session...")
        
        if os.name == 'posix':
            os.killpg(os.getpgid(process.pid), signal.SIGINT)
        else:
            raise NotImplementedError("SIGINT is not supported on Windows")
        
        # Wait up to 5 minutes for graceful shutdown
        if not wait_for_completion(process, timeout_minutes=5):
            print("Process not responding to SIGINT. Force killing...")
            if os.name == 'posix':
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            else:
                process.kill()
            process.wait()
    
    except KeyboardInterrupt:
        # Handle manual interruption the same way
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"Process terminated by user")
        if os.name == 'posix':
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        else:
            process.kill()
        process.wait()
    
    # Brief pause for cleanup
    time.sleep(2)

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

def run_experiment(user_id: str, model_name: str, use_baseline: bool, max_turns: int, restart) -> str:
    """Run a single experiment with the specified configuration
    
    Args:
        user_id (str): User ID for the experiment
        model_name (str): Name of the model to use
        use_baseline (bool): Whether to use baseline prompt
        max_turns (int): Maximum number of turns for the session
        restart (bool): Whether to clear existing user data before running
                       (Note: This is typically handled by the calling script now)
    
    Returns:
        str: The experiment ID
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    experiment_id = f"{model_name.replace('-', '_')}_baseline_" \
                   f"{str(use_baseline).lower()}_{timestamp}"
    
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
          f"Starting experiment: {experiment_id}")
    
    # Set up environment variables and directories
    if use_baseline:
        logs_dir = f"logs_{model_name.replace('-', '_')}"
        data_dir = f"data_{model_name.replace('-', '_')}"
        update_env_file(model_name, use_baseline, logs_dir, data_dir)
    else:
        logs_dir = "logs"
        data_dir = "data"
        update_env_file(model_name, use_baseline, logs_dir, data_dir)
    
    # Create directories if they don't exist
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    
    # Run the interview session
    command = f"python src/main.py --mode terminal --user_id {user_id} --user_agent --max_turns {max_turns}" + \
              (f" --restart" if restart else "")
    run_command_with_timeout(command, 30)
    
    # Run evaluations
    eval_results: Dict[str, str] = {}
    for eval_type in ["biography_completeness", "biography_groundedness"]:
        success = run_evaluation(user_id, eval_type)
        eval_results[eval_type] = "Success" if success else "Failed"
    
    # Log experiment results
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
          f"Experiment completed: {experiment_id}")
    print(f"Model: {model_name}")
    print(f"Baseline: {use_baseline}")
    print(f"User ID: {user_id}")
    print(f"Max Turns: {max_turns}")
    print(f"Logs directory: {logs_dir}")
    print(f"Data directory: {data_dir}")
    print("Evaluation results:")
    for eval_type, result in eval_results.items():
        print(f"  - {eval_type}: {result}")
    
    # Add a clear separator between experiments
    print("\n" + "="*80 + "\n")
    
    return experiment_id 