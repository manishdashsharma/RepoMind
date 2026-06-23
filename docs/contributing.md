# Contributing to Zeocloud

Zeocloud is open source and contributions are welcome. This document explains how to set up a dev environment, the module structure, and what good contributions look like.

---

## Development Setup

```bash
git clone https://github.com/manishdashsharma/Zeocloud
cd Zeocloud

# Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies including dev tools
uv sync --dev

# Run the CLI locally
uv run zeocloud install
uv run zeocloud
```

---

## Code Quality

```bash
# Lint
uv run ruff check src/

# Format
uv run ruff format src/

# Type check
uv run mypy src/

# Tests
uv run pytest tests/
```

All four must pass before opening a PR. CI runs all of them on Python 3.11 and 3.12.

---

## Project Structure

```
src/
  cli/
    main.py          ← Typer app, commands: install / status / (default)
    install.py       ← zeocloud install wizard
    chat.py          ← Interactive Q&A loop
  config/
    settings.py      ← ZeocloudConfig Pydantic model, load/save
  llm/
    ollama.py        ← httpx client for Ollama REST API
  embedder/
    embed.py         ← EmbedClient wrapping Ollama embeddings
  indexer/
    indexer.py       ← Repo walk, tiktoken chunking, language detection
  retriever/
    qdrant.py        ← VectorStore (Qdrant CRUD)
    pipeline.py      ← RAGPipeline (embed → search → generate)
  utils/
    display.py       ← Rich console, banners, spinners, tables
    system.py        ← Hardware detection, model recommendations
    safety.py        ← Path validation, sensitive file detection
    session.py       ← SessionData, save_session()
```

---

## Code Conventions

These are non-negotiable:

- `from __future__ import annotations` on every file
- Type hints on every function signature
- No inline comments — naming must explain intent
- 100 char line limit (enforced by ruff)
- Named exports — no wildcard imports
- Services raise plain `Exception` with a message; CLI layer catches and displays
- Never `print()` directly — always use `display.console` or the helper functions (`success()`, `error()`, `info()`, etc.)

---

## Adding a New Language to the Indexer

`src/indexer/indexer.py` has a `_LANGUAGE_MAP` dict mapping file extensions to language names. Add your extension there:

```python
".nim": "nim",
".zig": "zig",
```

No other changes needed — the chunker and embedder are language-agnostic.

---

## Adding a New CLI Command

1. Add a function decorated with `@app.command("name")` in `src/cli/main.py`
2. Keep logic in a dedicated module if it's more than ~20 lines
3. Use `section()`, `success()`, `error()` from `display.py` for consistent UI

---

## PR Guidelines

- One concern per PR — don't bundle unrelated changes
- Write a clear description of what and why
- Make sure `uv run ruff check src/` and `uv run pytest tests/` pass
- If you add a new module, add tests under `tests/`

---

## Ideas for Contributions

- **More languages**: add extensions to `_LANGUAGE_MAP` in `indexer.py`
- **Smarter chunking**: chunk by function/class boundaries using tree-sitter
- **Multiple embed models**: let users choose embed model at install (instead of always `nomic-embed-text`)
- **Export session to HTML**: pretty-print Q&A sessions as a shareable HTML file
- **Project diff detection**: detect when source files changed and suggest re-indexing
- **Shell completion**: improve the auto-complete experience for `zeocloud` subcommands

---

## Reporting Bugs

Open an issue at https://github.com/manishdashsharma/Zeocloud/issues

Include `zeocloud status` output and the full error message.
