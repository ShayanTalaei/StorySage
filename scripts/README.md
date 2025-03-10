# AI Autobiography Experiment Runner

This directory contains scripts for running experiments with different configurations for the AI Autobiography project.

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

### Analyzing Results

```bash
# Analyze results for a single user
./scripts/analyze_results.sh coates

# Analyze results for multiple users
./scripts/analyze_results.sh coates ellie alex
```

## Parameters

### Multiple Experiments

- `--user_id`: (Required) User ID for the experiment
- `--timeout`: (Optional) Timeout in minutes for each session (default: 8)
- `--skip_baseline`: (Optional) Skip baseline experiments
- `--restart`: (Optional) Clear existing user data before running

### Single Experiment

- `--user_id`: (Required) User ID for the experiment
- `--model`: (Optional) Model to use (default: gpt-4o)
- `--baseline`: (Optional) Use baseline prompt
- `--timeout`: (Optional) Timeout in minutes for the session (default: 8)
- `--restart`: (Optional) Clear existing user data before running

## Experiment Configurations

The multiple experiments script runs the following experiments:

1. Our work: `MODEL_NAME=gpt-4o`, `USE_BASELINE_PROMPT=false`
2. Baseline with GPT-4o: `MODEL_NAME=gpt-4o`, `USE_BASELINE_PROMPT=true`
3. Baseline with Gemini: `MODEL_NAME=gemini-1.5-pro`, `USE_BASELINE_PROMPT=true`

For baseline experiments, the script sets:

- `LOGS_DIR=logs_{model_name}`
- `DATA_DIR=data_{model_name}`

## Output Structure

The scripts create:

- A backup of the original `.env` file
- Logs and data for each experiment in their respective directories:
  - Our work: `logs/` and `data/`
  - Baseline experiments: `logs_{model_name}/` and `data_{model_name}/`

## Evaluations

After each experiment, the scripts run the following evaluations:

- Biography completeness
- Biography groundedness

## Example Workflow

```bash
# Run experiments for a user
./scripts/run_experiments.sh --user_id coates --timeout 10

# Analyze the results
./scripts/analyze_results.sh coates
```

## Important Notes

1. The scripts properly end each session by sending a keyboard interrupt (Ctrl+C) signal, which allows the application to perform necessary cleanup operations before terminating.

2. When analyzing results:
   - Baseline experiments are identified by logs in `logs_*` directories
   - Our work is identified by logs in the main `logs` directory
   - Statistics are averaged across sessions and experiments 