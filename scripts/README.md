# AI Autobiography Experiment Runner

This directory contains scripts for running experiments with different configurations for the AI Autobiography project.

## Running Experiments

### Single Session Experiment

```bash
# Basic usage with user ID
./scripts/run_single_experiment.sh --user_id coates

# Run with a specific model
./scripts/run_single_experiment.sh --user_id coates --model gemini-1.5-pro

# Run with baseline prompt
./scripts/run_single_experiment.sh --user_id coates --baseline

# Specify a custom number of turns
./scripts/run_single_experiment.sh --user_id coates --max_turns 20
```

### Single Session with All Models

```bash
# Basic usage with user ID
./scripts/run_experiments.sh --user_id coates

# Specify a custom number of turns
./scripts/run_experiments.sh --user_id coates --max_turns 20

# Start fresh by clearing previous data
./scripts/run_experiments.sh --user_id coates --restart
```

### Multiple Sessions with All Models

```bash
# Basic usage with user ID (default 10 sessions)
./scripts/run_multiple_sessions.sh --user_id coates

# Run 5 sessions with 20 turns each
./scripts/run_multiple_sessions.sh --user_id coates --num_sessions 10 --max_turns 20 --restart
```

## Running Comparisons

### Comparison for a Single Session

```bash
# Run both biography and interview comparisons for a session
./scripts/run_single_comparison.sh --session_id 1 coates

# Run only biography comparisons
./scripts/run_single_comparison.sh --type bio --session_id 1 coates

# Run only interview comparisons
./scripts/run_single_comparison.sh --type interview --session_id 1 coates

# Run with specific number of comparison runs
./scripts/run_single_comparison.sh --run_times 5 coates
```

### Comparison Across All Sessions

```bash
# Run interview comparisons for all sessions and biography for latest session
./scripts/run_all_comparisons.sh coates

# Run with specific number of comparison runs per session
./scripts/run_all_comparisons.sh --run_times 5 coates

# Run for multiple users
./scripts/run_all_comparisons.sh coates ellie alex
```

## Parameters

### Multiple Sessions

- `--user_id`: (Required) User ID for the experiment
- `--num_sessions`: (Optional) Number of sessions to run (default: 10)
- `--max_turns`: (Optional) Maximum turns per session (default: 20)

### Single Session

- `--user_id`: (Required) User ID for the experiment
- `--model`: (Optional) Model to use (default: gpt-4o)
- `--baseline`: (Optional) Use baseline prompt
- `--max_turns`: (Optional) Maximum turns (default: 20)
- `--restart`: (Optional) Clear existing data before running

### Comparisons

- `--run_times`: (Optional) Number of comparison runs (default: 5)
- `--session_id`: (Optional) Specific session to evaluate
- `--type`: (Optional) Type of comparison: "bio" or "interview"

## Output Structure

The scripts create:
- Our work: `logs/` and `data/`
- Baseline experiments: `logs_{model_name}/` and `data_{model_name}/`
