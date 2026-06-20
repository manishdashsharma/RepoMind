from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

REPOMIND_DIR = Path.home() / ".repomind"
CONFIG_FILE = REPOMIND_DIR / "config.json"
SESSIONS_DIR = REPOMIND_DIR / "sessions"


class ProjectEntry(BaseModel):
    name: str
    path: str
    indexed_at: str
    file_count: int = 0
    chunk_count: int = 0


class RepoMindConfig(BaseModel):
    agent_name: str | None = None
    model: str = "llama3.2:3b"
    embed_model: str = "nomic-embed-text"
    installed: bool = False
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    ollama_host: str = "http://localhost:11434"
    projects: dict[str, ProjectEntry] = Field(default_factory=dict)

    @field_validator("ollama_host")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")


def load_config() -> RepoMindConfig:
    REPOMIND_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        config = RepoMindConfig()
        _write(config)
        return config
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return RepoMindConfig.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        config = RepoMindConfig()
        _write(config)
        return config


def save_config(config: RepoMindConfig) -> None:
    REPOMIND_DIR.mkdir(parents=True, exist_ok=True)
    _write(config)


def _write(config: RepoMindConfig) -> None:
    CONFIG_FILE.write_text(config.model_dump_json(indent=2), encoding="utf-8")
