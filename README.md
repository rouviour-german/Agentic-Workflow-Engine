# Agentic Workflow Engine

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An operating system for agents — a general-purpose engine that decomposes ANY complex goal into a dynamic DAG (Directed Acyclic Graph) of subtasks, executes them with parallelism, handles failures through replanning, tracks costs, and includes human-in-the-loop checkpoints. 

## Features

- **DAG-based Execution**: Accepts natural language goals, decomposes them into atomic parallel subtasks using a DeepSeek-based planner.
- **Parallel Subtasks**: Runs independent tasks concurrently using AsyncIO.
- **Adaptive Execution**: When failure occurs, chooses between `RETRY`, `REPLAN`, or `ESCALATE` to adapt at runtime.
- **Cost Awareness**: Tracks model costs continuously to enforce budget constraints across execution phases.
- **Human In The Loop**: Requests human approval before high-stakes operations or when a budget is exceeded.
- **DeepSeek Integration**: Uses the reliable `deepseek-chat` model for robust planning and execution operations.

## Technology Stack

- **Python 3.10+**
- **DeepSeek API**: `deepseek-chat` model replacing expensive legacy models.
- **NetworkX**: Verifies DAG topological bounds and detects cycles.
- **Pydantic**: Heavily utilized for data validation and parsing JSON outputs.

## Setup & Run

1. Clone the repository
2. Set up the Environment (Requires Python 3.10+) 
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and assign your API key. Make sure `DEEPSEEK_API_KEY` is present.
4. Run the Engine CLI:
   ```bash
   python main.py run "Evaluate three top web scraping libraries for python, compare their features and write a summary."
   ```

## Engine Architecture 

- **Planner**: `GoalDecomposer`, `DAGValidator`, `CostEstimator`, `DynamicReplanner`
- **Executor**: `ParallelExecutor`, `WorkflowScheduler`, `DependencyResolver`
- **Failure Engine**: Error Classification and Strategies (`RETRY`, `REPLAN`, `SKIP`, `ESCALATE`)
- **Monitoring**: Live event traces with Cost Analysis.

## Subtask Node Execution Example (CLI Trace Representation)

```text
▶ Executing...
[0.0s] 🚀 Started: research_competitors, research_market, analyze_strengths (parallel)
[3.2s] ✅ research_competitors completed ($0.04, 823 tokens)
[4.1s] ✅ analyze_strengths completed ($0.03, 612 tokens)
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

---

---

## Author & Contact

- **GitHub:** [@rouviour-german](https://github.com/rouviour-german)
- **Email:** [rouviourgermanmeetings@gmail.com](mailto:rouviourgermanmeetings@gmail.com)
- **Profile:** https://github.com/rouviour-german

