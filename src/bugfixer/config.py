"""Configuration – LLM provider, LangSmith tracing, and runtime settings."""

from __future__ import annotations

import os

from langchain_openai import ChatOpenAI


def get_llm(
    model: str | None = None,
    temperature: float = 0.0,
) -> ChatOpenAI:
    """Return a configured ChatOpenAI instance.

    Reads OPENAI_API_KEY from the environment.  Model defaults to
    ``BUGFIXER_MODEL`` env-var, falling back to ``gpt-4o``.
    """
    model = model or os.getenv("BUGFIXER_MODEL", "gpt-4o")
    return ChatOpenAI(model=model, temperature=temperature)


def configure_langsmith() -> None:
    """Enable LangSmith tracing when credentials are present."""
    if os.getenv("LANGSMITH_API_KEY"):
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        os.environ.setdefault("LANGSMITH_PROJECT", "bugfixer")
