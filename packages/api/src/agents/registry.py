# This project was developed with assistance from AI tools.
"""Agent registry -- loads agent configs and returns configured graphs.

Each agent is defined by a YAML file in config/agents/ and backed by
a Python module in this package that builds the LangGraph graph.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_AGENTS_CONFIG_DIR = Path(__file__).resolve().parents[4] / "config" / "agents"

# Lazy-loaded agent graph cache
_graphs: dict[str, Any] = {}


def load_agent_config(agent_name: str) -> dict[str, Any]:
    """Load a single agent's YAML config."""
    config_path = _AGENTS_CONFIG_DIR / f"{agent_name}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Agent config not found: {config_path}")
    return yaml.safe_load(config_path.read_text())


def get_agent(agent_name: str):
    """Return a compiled LangGraph graph for the named agent.

    Graphs are cached after first build. Currently only 'public-assistant'
    is implemented; future agents will be added here.
    """
    if agent_name in _graphs:
        return _graphs[agent_name]

    config = load_agent_config(agent_name)

    if agent_name == "public-assistant":
        from .public_assistant import build_graph

        graph = build_graph(config)
    else:
        raise ValueError(f"Unknown agent: {agent_name}")

    _graphs[agent_name] = graph
    return graph


def list_agents() -> list[str]:
    """Return names of all available agents (based on YAML files on disk)."""
    if not _AGENTS_CONFIG_DIR.exists():
        return []
    return [p.stem for p in _AGENTS_CONFIG_DIR.glob("*.yaml")]
