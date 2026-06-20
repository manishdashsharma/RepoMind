# RepoMind — AI Context

## What this project is
Open-source CLI tool that lets developers ask questions about any local codebase in English or Hindi — running 100% locally via Ollama (LLM + embeddings) and Qdrant (vector DB in Docker).

## Tech stack
- **Language**: Python 3.11+ managed with `uv`
- **CLI**: Typer + Rich (colorful terminal UI)
- **LLM / Embeddings**: Ollama (local, no cloud)
- **Vector DB**: Qdrant running in Docker
- **Chunking tokens**: tiktoken (`cl100k_base`)
- **Gitignore handling**: pathspec

## Project layout
```
src/repomind/
  cli/
    main.py          ← Typer root app, agent naming, menu routing
    install.py       ← repomind install — setup wizard
    chat.py          ← interactive Q&A loop, project indexing
  core/
    rag.py           ← embed → search → generate pipeline
    indexer.py       ← repo walk, chunking, language detection
    vector_store.py  ← Qdrant CRUD (upsert, search, delete)
  config/
    settings.py      ← RepoMindConfig pydantic model, load/save ~/.repomind/config.json
  utils/
    display.py       ← Rich console, banner, spinners, tables, panels
    system.py        ← CPU/RAM/GPU detection, model recommendation matrix
    ollama_client.py ← httpx wrapper for Ollama REST API
```

## Config location
`~/.repomind/config.json` — agent name, model, indexed projects list, service URLs.

## Session files
After every chat session a markdown file is written to `~/.repomind/sessions/{YYYY-MM-DD_HH-MM-SS}.md`.  
Format: header (agent, duration, question count) + full Q&A log.

## Code conventions (non-negotiable)
- `from __future__ import annotations` on every file
- Type hints on every function signature
- No inline comments — naming must explain intent
- 100 char line limit
- Named exports — no wildcard imports
- Services throw plain `Exception` with a message; CLI layer catches and displays
- Never print directly — always use `display.console` or the helper functions

## Running locally
```bash
uv sync
uv run repomind install   # first-time setup
uv run repomind           # start chatting
```

## Tests
```bash
uv run pytest tests/
uv run ruff check src/
uv run mypy src/
```

## Key design decisions
1. **One Qdrant collection per project** — prefixed `repomind_{project_name}`
2. **nomic-embed-text** always used for embeddings (dim=768, fast, good code understanding)
3. **Chunk size**: 400 tokens, 80-token overlap — balances context vs precision
4. **Model selection**: based on detected RAM + GPU at install time (see `utils/system.py`)
5. **Hindi support**: llama3.1:8b+ handles Hindi well; noted in model recommendations
