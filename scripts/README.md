# AI Autobiography Experiment Runner

This directory contains scripts for running experiments with different configurations for the AI Autobiography project.

## Scripts

1. `run_experiments.py` / `run_experiments.sh` - Run multiple experiments with different configurations
2. `run_single_experiment.py` / `run_single_experiment.sh` - Run a single experiment with a specific configuration
3. `experiment_utils.py` - Common utilities used by both experiment scripts

## Features

- Runs experiments with different models and configurations
- Automatically terminates sessions after a specified timeout
- Runs evaluations after each session
- Backs up and restores the original `.env` file

## Usage

### Running Multiple Experiments

```bash
# Basic usage with user ID
./scripts/run_experiments.sh --user_id coates

# Specify a custom timeout (in minutes)
./scripts/run_experiments.sh --user_id coates --timeout 15

# Skip baseline experiments (only run our work)
./scripts/run_experiments.sh --user_id coates --skip_baseline

# Alternatively, you can run the Python script directly
python scripts/run_experiments.py --user_id coates --timeout 15
```

### Running a Single Experiment

```bash
# Basic usage with user ID (defaults to gpt-4o without baseline)
./scripts/run_single_experiment.sh --user_id coates

# Run with a specific model
./scripts/run_single_experiment.sh --user_id coates --model gemini-1.5-pro

# Run with baseline prompt
./scripts/run_single_experiment.sh --user_id coates --baseline

# Specify a custom timeout (in minutes)
./scripts/run_single_experiment.sh --user_id coates --timeout 15

# Alternatively, you can run the Python script directly
python scripts/run_single_experiment.py --user_id coates --model gpt-4o --baseline --timeout 15
```

## Parameters

### Multiple Experiments

- `--user_id`: (Required) User ID for the experiment
- `--timeout`: (Optional) Timeout in minutes for each session (default: 10)
- `--skip_baseline`: (Optional) Skip baseline experiments

### Single Experiment

- `--user_id`: (Required) User ID for the experiment
- `--model`: (Optional) Model to use (default: gpt-4o)
- `--baseline`: (Optional) Use baseline prompt
- `--timeout`: (Optional) Timeout in minutes for the session (default: 10)

## Experiment Configurations

The multiple experiments script runs the following experiments:

1. Our work: `MODEL_NAME=gpt-4o`, `USE_BASELINE_PROMPT=false`
2. Baseline with GPT-4o: `MODEL_NAME=gpt-4o`, `USE_BASELINE_PROMPT=true`
3. Baseline with Gemini: `MODEL_NAME=gemini-1.5-pro`, `USE_BASELINE_PROMPT=true`

For baseline experiments, the script sets:

- `LOGS_DIR=logs_{model_name}`
- `DATA_DIR=data_{model_name}`

## Code Structure

The experiment scripts are organized as follows:

- `experiment_utils.py` - Contains common utilities used by both experiment scripts:
  - Environment file management (backup, restore, update)
  - Running commands with proper timeout handling
  - Running evaluations
  - Core experiment functionality

- `run_experiments.py` - Uses the utilities to run multiple experiments
- `run_single_experiment.py` - Uses the utilities to run a single experiment

This modular structure eliminates code duplication and makes the scripts more maintainable.

## Output

The scripts create:

- A backup of the original `.env` file
- Logs and data for each experiment in their respective directories

## Evaluations

After each experiment, the scripts run the following evaluations:

- Biography completeness
- Biography groundedness

## Example

```bash
# Run multiple experiments
./scripts/run_experiments.sh --user_id coates --timeout 10

# Run a single experiment
./scripts/run_single_experiment.sh --user_id coates --model gpt-4o --baseline --timeout 10
```

## Important Note

The scripts properly end each session by sending a keyboard interrupt (Ctrl+C) signal, which allows the application to perform necessary cleanup operations before terminating. This is important for ensuring that all data is properly saved and processed. 