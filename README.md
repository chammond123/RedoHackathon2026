# BugFixer – Agentic Debugging System

An autonomous debugging agent that reproduces, diagnoses, and fixes software bugs.
Built with **LangChain + LangGraph** for a hackathon.

## Quick Start

```bash
# Install in editable mode
pip install -e ".[dev]"

# Create a .env file with your environment variables (required)
# OPENAI_API_KEY="sk-..."
# LANGSMITH_TRACING=true
# LANGSMITH_API_KEY="ls-..."
# LANGSMITH_PROJECT="bugfixer"

# Run the agent
bugfixer run

# Or point it at a specific repo
bugfixer run --repo /path/to/target/repo
```

## Architecture

```
User bug report (CLI)
  → intake_context        – scan codebase, gather environment info
  → hypothesis_generation – form reproduction hypotheses
  → reproduction_attempt  – run tests / scripts to reproduce
  → reproduction_analysis – verify reproduction succeeded
        ↑ retry loop if reproduction fails
  → root_cause_analysis   – identify minimal root cause
  → patch_generation      – generate and apply a fix
  → validation            – re-run tests, verify fix
        ↑ retry loop if validation fails
  → completion            – summarize findings, prepare PR artifacts
```

All phases read from and write to a shared **AgentState** dict,
and append human-readable logs at every step.

## Project Layout

```
src/bugfixer/
├── __init__.py
├── __main__.py          # python -m bugfixer
├── cli.py               # Click CLI
├── config.py            # LLM + LangSmith configuration
├── state.py             # AgentState schema
├── graph.py             # LangGraph state machine
├── nodes/               # One module per graph node
│   ├── __init__.py
│   ├── intake.py
│   ├── hypothesis.py
│   ├── reproduce.py
│   ├── analyze.py
│   ├── root_cause.py
│   ├── patch.py
│   ├── validate.py
│   └── complete.py
└── tools/               # Deterministic helper tools
    ├── __init__.py
    ├── codebase.py      # File reading, search, listing
    ├── runner.py         # Shell / test execution
    └── patch.py          # Diff generation & application
tests/
├── __init__.py
└── test_graph.py
```