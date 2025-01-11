#!/bin/bash
eval "$(conda shell.bash hook)"
conda activate interview-agent

python src/user_agent.py
