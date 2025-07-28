# StorySage

> **StorySage: Conversational Autobiography Writing Powered by a Multi-Agent Framework**  
> Shayan Talaei, Meijin Li, Kanu Grover, James Kent Hippler, Diyi Yang, Amin Saberi  
> arXiv:2506.14159 [cs.HC], 2025  
> [Paper](https://arxiv.org/abs/2506.14159)

## Overview

StorySage is a multi-agent AI system for 
conducting biographical interviews and generating 
autobiographies. The system uses specialized AI 
agents to conduct natural conversations, manage 
memory, and generate structured biographical 
content.

Our framework offers:

- 🤖 Multi-agent architecture for distributed task handling
- 🧠 Memory bank for long-term conversation context
- ❓ Dynamic question generation and topic management
- ✍️ Concurrent biography writing and updates
- 🎮 User-driven conversation control and editing interface

## System Architecture

StorySage operates through three main stages, each powered by specialized agents as shown in Figure 1:

![StorySage Multi-Agent Architecture](images/storysage_multiagent_architecture.pdf.png)
*Figure 1: Overview of StorySage's multi-agent architecture*

1.**User Interview**

- **Interviewer Agent**: Conducts natural conversations and manages user interaction
- **Session Scribe Agent**: Processes conversation data, manages memory storage, and generates follow-up questions

2.**Biography Writing**

- **Planner Agent**: Analyzes biography structure and creates content update plans
- **Section Writer Agent**: Generates narrative content based on planner guidelines

3.**Session Planning**

- **Session Coordinator Agent**: Prepares agendas for future sessions and maintains conversation continuity

## Setup

### Requirements

- Python 3.12+
- Environment variables (see `.env.example`)

### Installation

```bash
pip install -r requirements.txt
```

## Usage

Run the interviewer:

```bash
python src/main.py --mode terminal --user_id <USER_ID>
```

### Optional Parameters

- `--user_agent`: Enable user agent mode
- `--voice_output`: Enable voice output
- `--voice_input`: Enable voice input
- `--restart`: Clear previous session data

### Notes

- Use the same `--user_id` to continue previous conversations
- Biographies are saved in `data/<user_id>/biography_*.json`
- Press Ctrl+C and Enter once to end a session

## Citation

If you find this work helpful, please cite our paper:

```bibtex
@misc{talaei2025storysageconversationalautobiographywriting,
      title={StorySage: Conversational Autobiography Writing Powered by a Multi-Agent Framework}, 
      author={Shayan Talaei and Meijin Li and Kanu Grover and James Kent Hippler and Diyi Yang and Amin Saberi},
      year={2025},
      eprint={2506.14159},
      archivePrefix={arXiv},
      primaryClass={cs.HC},
      url={https://arxiv.org/abs/2506.14159}, 
}
```