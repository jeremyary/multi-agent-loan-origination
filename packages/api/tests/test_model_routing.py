# This project was developed with assistance from AI tools.
"""Tests for model routing config loading and query classification."""

import textwrap
from pathlib import Path

import pytest

from src.inference import config as config_mod
from src.inference.config import _resolve_env_vars, load_config
from src.inference.router import classify_query


@pytest.fixture(autouse=True)
def _reset_config_cache():
    """Reset the config module cache before each test."""
    config_mod._cached_config = None
    config_mod._cached_mtime = 0.0
    original_path = config_mod._CONFIG_PATH
    yield
    config_mod._CONFIG_PATH = original_path
    config_mod._cached_config = None
    config_mod._cached_mtime = 0.0


def _write_standard_config(tmp_path: Path) -> None:
    """Write a standard test config and point the module at it."""
    cfg = tmp_path / "models.yaml"
    cfg.write_text(
        textwrap.dedent("""\
        routing:
          default_tier: capable_large
          classification:
            strategy: rule_based
            rules:
              simple:
                max_query_words: 10
                requires_tools: false
                patterns: ["status", "when", "what is", "show me", "how much"]
              complex:
                default: true
        models:
          fast_small:
            provider: openai_compatible
            model_name: test-small
            endpoint: http://localhost:8000/v1
          capable_large:
            provider: openai_compatible
            model_name: test-large
            endpoint: http://localhost:8000/v1
        """)
    )
    config_mod._CONFIG_PATH = cfg


# -- Config validation --


def test_load_config_rejects_missing_model_fields(tmp_path):
    """Should reject a model missing required fields."""
    cfg = tmp_path / "models.yaml"
    cfg.write_text(
        textwrap.dedent("""\
        routing:
          default_tier: fast_small
        models:
          fast_small:
            provider: openai_compatible
        """)
    )
    with pytest.raises(ValueError, match="missing required fields"):
        load_config(cfg)


def test_load_config_rejects_bad_default_tier(tmp_path):
    """Should reject default_tier pointing to nonexistent model."""
    cfg = tmp_path / "models.yaml"
    cfg.write_text(
        textwrap.dedent("""\
        routing:
          default_tier: nonexistent
        models:
          fast_small:
            provider: openai_compatible
            model_name: test
            endpoint: http://localhost:8000/v1
        """)
    )
    with pytest.raises(ValueError, match="does not match any model"):
        load_config(cfg)


def test_env_var_substitution(monkeypatch):
    """Should resolve ${VAR:-default} from environment."""
    monkeypatch.setenv("TEST_LLM_URL", "http://my-server:8080")
    result = _resolve_env_vars({"endpoint": "${TEST_LLM_URL:-http://fallback}"})
    assert result["endpoint"] == "http://my-server:8080"


def test_env_var_uses_default_when_unset():
    """Should use the default when env var is not set."""
    result = _resolve_env_vars({"endpoint": "${DEFINITELY_UNSET_VAR:-http://fallback}"})
    assert result["endpoint"] == "http://fallback"


# -- Query classification --


def test_classify_simple_pattern_routes_fast(tmp_path):
    """Short query matching a simple pattern should route to fast_small."""
    _write_standard_config(tmp_path)
    assert classify_query("What is my rate?") == "fast_small"


def test_classify_long_query_routes_complex(tmp_path):
    """Query exceeding max_query_words should route to capable_large."""
    _write_standard_config(tmp_path)
    result = classify_query(
        "I want to understand the full implications of refinancing my thirty year "
        "fixed rate mortgage into a fifteen year adjustable rate product"
    )
    assert result == "capable_large"


def test_classify_tools_required_routes_complex(tmp_path):
    """Queries requiring tools always route to capable_large regardless of content."""
    _write_standard_config(tmp_path)
    assert classify_query("Show me", requires_tools=True) == "capable_large"
