# GEMINI.md - Biomni Project Context

## Project Overview

Biomni is a general-purpose biomedical AI agent designed to autonomously execute a wide range of research tasks across diverse biomedical subfields. It integrates large language model (LLM) reasoning with retrieval-augmented planning and code-based execution to enhance research productivity and generate testable hypotheses.

The core agent, `A1`, is implemented in Python and can utilize various LLM providers (Anthropic, OpenAI, Ollama, etc.). It operates by interpreting natural language commands, planning a sequence of actions using available tools, and executing code to achieve the task.

### Key Technologies

*   **Python**: The primary programming language.
*   **LangChain / LangGraph**: Used for building the agent's workflow and managing LLM interactions.
*   **Pydantic**: For data validation and settings management.
*   **Conda**: Environment management, with a complex setup script (`biomni_env/setup.sh`) for installing numerous bioinformatics tools and dependencies (E1 environment).
*   **MCP (Model Context Protocol)**: Supported for integrating external tools and servers.

## Project Structure

*   `biomni/`: Main Python package source code.
*   `biomni/agent/`: Contains the core agent logic (e.g., `A1` class in `a1.py`).
*   `biomni/tool/`: Houses individual tools (Python functions) available to the agent.
*   `biomni/tool/tool_description/`: Contains descriptions of tools for the agent's use.
*   `biomni/task/`: Defines benchmarks and evaluation tasks.
*   `biomni/model/`: Related to LLM and retriever models.
*   `biomni_env/`: Scripts and configurations for setting up the Python/Bioinformatics environment (E1 is the full environment).
*   `docs/`: Project documentation.
*   `tutorials/`: Example notebooks and guides.
*   `data/` (user-created): Default directory for data storage and downloads.

## Installation and Setup

1.  **Environment Setup**:
    *   The project requires a specific Python environment. A basic environment can be set up with `conda env create -f biomni_env/environment.yml`.
    *   For the full suite of tools (E1), a comprehensive setup script `biomni_env/setup.sh` must be run. This process is lengthy (>10 hours) and requires substantial disk space (30GB+).
    *   Updates to the environment are managed via scripts like `biomni_env/new_software_v004.sh`.

2.  **Package Installation**:
    *   After setting up the Conda environment (`conda activate biomni_e1`), the official `biomni` package can be installed via `pip install biomni` or directly from the source `pip install git+https://github.com/snap-stanford/Biomni.git@main`.

3.  **Configuration**:
    *   API keys for LLM providers (Anthropic, OpenAI, etc.) are required. These should be configured using a `.env` file (copied from `.env.example`) or environment variables.

4.  **Known Conflicts**:
    *   Some packages (e.g., `hyperimpute`, `langchain_aws`) are not installed by default due to dependency conflicts. They need to be installed manually if needed, and relevant code may need to be uncommented.

## Core Agent Usage (`A1`)

The main interface is the `A1` class in `biomni.agent.a1`.

```python
from biomni.agent import A1

# Initialize the agent
# Downloads data lake on first run (~11GB)
agent = A1(path='./data')

# Specify a different model
agent = A1(path='./data', llm='claude-3-5-sonnet-20241022')

# Execute tasks using natural language
agent.go("Plan a CRISPR screen to identify genes that regulate T cell exhaustion.")
```

## Development and Contribution

Biomni is an open-science project welcoming contributions in tools, datasets, software integration, benchmarks, tutorials, and more.

*   **Adding a New Tool**:
    *   Implement a Python function in `biomni/tool/XXX.py`.
    *   Create a description in `biomni/tool/tool_description/XXX.py`.
    *   Test thoroughly and submit a PR.
*   **Adding New Data**:
    *   For web APIs, add a query function and description.
    *   For downloadable data, add an entry to `data_lake_dict` in `biomni/env_desc.py`.
*   **Adding New Software**:
    *   Create an installation script, update `biomni_env/new_software_{VERSION}.sh`, and add to `library_content_dict` in `biomni/env_desc.py`.
*   **Adding a New Benchmark**:
    *   Implement a class in `biomni/task/` following a specific interface.
*   **Bug Fixes & Enhancements**:
    *   Welcome! Create an issue first to discuss.

See [CONTRIBUTION.md](CONTRIBUTION.md) for detailed guidelines.

## Important Notes

*   **Security**: The agent executes LLM-generated code with full system privileges. Use only in isolated/sandboxed environments, especially with sensitive data.
*   **Licensing**: While Biomni itself is Apache 2.0, integrated tools or data may have more restrictive licenses.
*   **Current State**: This repository represents a snapshot (frozen as of April 15, 2025) and may differ from the active web platform.
