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


def get_strict_verification() -> bool:
    """Check if strict verification mode is enabled.
    
    When enabled, the validation step will FAIL if the verification test
    does not pass after applying the patch. This provides stronger
    guarantees that fixes actually address the root cause.
    
    Set via BUGFIXER_STRICT_VERIFICATION=true environment variable.
    """
    return os.getenv("BUGFIXER_STRICT_VERIFICATION", "false").lower() in ("true", "1", "yes")


def get_skip_verification() -> bool:
    """Check if verification test generation should be skipped.
    
    When enabled, the verify_hypothesis step will be skipped entirely.
    Useful for faster runs when you trust the existing tests.
    
    Set via BUGFIXER_SKIP_VERIFICATION=true environment variable.
    """
    return os.getenv("BUGFIXER_SKIP_VERIFICATION", "false").lower() in ("true", "1", "yes")
