# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Biomni is a general-purpose biomedical AI agent that combines LLM reasoning with retrieval-augmented planning and code execution. The agent can autonomously execute biomedical research tasks across diverse subfields.

## Environment Setup

### Prerequisites
- Python ≥3.11
- Conda environment manager
- API keys: ANTHROPIC_API_KEY (required), OPENAI_API_KEY (optional)

### Quick Setup
```bash
# Basic environment (fast)
conda env create -f biomni_env/environment.yml
conda activate biomni_e1

# Install package
pip install biomni --upgrade

# Full environment with all tools (~10 hours, 30GB disk)
cd biomni_env && bash setup.sh
```

### Docker Development
```bash
# Basic development
docker compose --profile basic up

# Full environment 
docker compose --profile full up

# Development with source mounting
docker compose --profile dev up
```

## Development Commands

### Code Quality
```bash
# Linting and formatting (uses ruff)
ruff check .
ruff format .

# Type checking
# No specific command - uses pyproject.toml config
```

### Package Management
```bash
# Build package
pip install -e .

# Install from source
pip install -e .
```

### Testing
The project excludes test files in pyproject.toml but has no formal test suite configured. Individual tools should be tested manually or via example notebooks.

## Core Architecture

### Agent System (biomni/agent/)
- **A1**: Main agent class that orchestrates LLM reasoning, tool selection, and execution
- Uses LangGraph for state management and tool orchestration
- Supports tool retrieval for dynamic tool selection
- Persistent Python execution environment via `run_python_repl`

### Tool System (biomni/tool/)
- **Modular by domain**: Each biomedical field has its own module (genetics.py, cancer_biology.py, etc.)
- **Tool Registry**: Central registry for tool discovery and validation
- **Tool Descriptions**: Metadata and schemas in tool_description/ folder
- **Database Tools**: Unified interface for querying biomedical databases
- **Support Tools**: Core utilities like Python REPL, file operations

### Data Layer (biomni/env_desc.py)
- **Data Lake**: ~11GB of curated biomedical datasets auto-downloaded on first run
- **Schema Database**: Pre-compiled database schemas in schema_db/
- **Library Content**: Descriptions of available software packages

### Task Framework (biomni/task/)
- **Base Task**: Abstract interface for benchmarks and evaluations
- **Specific Tasks**: HLE (lab bench), other biomedical benchmarks
- Required methods: `get_example()`, `evaluate()`, `output_class()`

## Usage Patterns

### Basic Agent Usage
```python
from biomni.agent import A1

# Initialize with data path (auto-downloads ~11GB on first run)
agent = A1(path='./data', llm='claude-sonnet-4-20250514')

# Execute tasks using natural language
agent.go("Your biomedical research task here")
```

### Adding New Tools
1. Implement function in appropriate `biomni/tool/[domain].py`
2. Add tool description in `biomni/tool/tool_description/[domain].py`
3. Use `biomni.utils.function_to_api_schema()` to auto-generate schemas
4. Test with agent execution

### Adding New Data Sources
1. For APIs: Add `query_XX` function to `database.py`
2. For static data: Add entry to `data_lake_dict` in `env_desc.py`
3. Ensure proper licensing and redistribution rights

## Important Notes

- Agent downloads large datasets (~11GB) automatically on first initialization
- Tool functions should be self-contained and well-documented
- All biomedical data sources require careful license compliance
- The system supports both local and Docker-based development workflows
- Code uses persistent Python namespaces for stateful execution across tool calls