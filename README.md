<div align="center">

```
 ██████╗ ███████╗██████╗  ██████╗ ███╗   ███╗██╗███╗   ██╗██████╗
 ██╔══██╗██╔════╝██╔══██╗██╔═══██╗████╗ ████║██║████╗  ██║██╔══██╗
 ██████╔╝█████╗  ██████╔╝██║   ██║██╔████╔██║██║██╔██╗ ██║██║  ██║
 ██╔══██╗██╔══╝  ██╔═══╝ ██║   ██║██║╚██╔╝██║██║██║╚██╗██║██║  ██║
 ██║  ██║███████╗██║     ╚██████╔╝██║ ╚═╝ ██║██║██║ ╚████║██████╔╝
 ╚═╝  ╚═╝╚══════╝╚═╝      ╚═════╝ ╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝
```

**Ask your codebase anything — locally, privately, powerfully.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![uv](https://img.shields.io/badge/managed%20by-uv-purple.svg)](https://github.com/astral-sh/uv)
[![Ollama](https://img.shields.io/badge/powered%20by-Ollama-black.svg)](https://ollama.com)
[![Qdrant](https://img.shields.io/badge/vector%20db-Qdrant-red.svg)](https://qdrant.tech)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

</div>

---

## What is RepoMind?

RepoMind is an open-source CLI tool that lets you have natural conversations with any codebase — in **English or Hindi** — without sending a single byte to the cloud.

It indexes your code locally, stores vectors in a local Qdrant database, and uses Ollama to run language models on your own hardware. No API keys. No subscriptions. No privacy concerns.

```bash
$ repomind

 ⚡ buddy is listening

  1.  Ask a question about your code
  2.  Index a new project

  You → buddy: auth middleware kahan hai aur kaise kaam karta hai?

  🤖 buddy:

  The auth middleware lives in `src/middleware/auth.js` (lines 12–48).
  It validates JWT tokens using the `jsonwebtoken` library...
```

---

## Features

- **100% local** — Ollama + Qdrant, zero cloud calls
- **Smart hardware detection** — suggests the right model for your machine (RAM, GPU, Apple Silicon)
- **Bilingual** — ask questions in English or Hindi, get answers in the same language
- **Conversation memory** — follow-up questions use previous context
- **Any language** — Python, JS, TS, Go, Rust, Java, C++, and 40+ more
- **Gitignore-aware** — skips `node_modules`, build artifacts, binary files
- **Safety guardrails** — blocks indexing of system directories, warns about `.env` files
- **Session logs** — every conversation is saved to `~/.repomind/sessions/`
- **Beautiful CLI** — Rich-powered colorful terminal with progress bars, spinners, tables
- **`repomind status`** — health check for all services at a glance

---

## Requirements

| Tool | Version | Purpose |
|------|---------|---------|
| [Python](https://python.org) | 3.11+ | Runtime |
| [uv](https://github.com/astral-sh/uv) | latest | Package manager |
| [Ollama](https://ollama.com/download) | latest | Local LLM |
| [Docker](https://www.docker.com/get-started) | latest | Vector database |

---

## Quick Start

### One-line install (macOS / Linux)

```bash
curl -LsSf https://raw.githubusercontent.com/manishdashsharma/RepoMind/main/scripts/install.sh | bash
```

### Manual install

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install RepoMind
uv tool install repomind

# 3. First-time setup (detects your hardware, pulls models, starts Qdrant)
repomind install
```

### Start chatting

```bash
repomind
```

That's it. Name your agent, point it at a project, and start asking questions.

---

## Usage

### `repomind install`

Interactive setup wizard that:
1. Detects your CPU, RAM, and GPU
2. Recommends the best local model for your hardware
3. Pulls the model via Ollama (downloads once, stored locally)
4. Starts Qdrant vector database in Docker
5. Runs health checks on all services

```
$ repomind install

  System Detection
  ┌──────────────┬──────────────────────────────────┐
  │ Property     │ Value                            │
  ├──────────────┼──────────────────────────────────┤
  │ OS           │ Darwin                           │
  │ CPU          │ Apple M3 Pro                     │
  │ CPU Cores    │ 11                               │
  │ RAM          │ 18.0 GB                          │
  │ Chip         │ Apple Silicon (unified memory)   │
  └──────────────┴──────────────────────────────────┘

  Recommended: llama3.1:8b  ★★★★☆ Great
```

### `repomind`

```
$ repomind

  ╔═══════════════════════════════════════╗
  ║           R E P O M I N D            ║
  ║    Ask your codebase anything         ║
  ╚═══════════════════════════════════════╝

  ── Name Your Agent ──────────────────────

  Give your AI assistant a name — something that feels right to you.
  Examples: buddy, sage, aria, max, nova, cody, orion

  Agent name [buddy]: aria

  ✓  aria is your RepoMind agent. Let's go!

  ⚡  aria is listening

  1.  Ask a question about your code
  2.  Index a new project
  3.  View indexed projects
  4.  Remove a project
  5.  Exit

  Choice [1]:
```

On **first run**, you name your AI agent — call it anything you like. That name is saved and used in every session going forward. Then the interactive menu appears:

- **Ask a question** — select a project and ask anything in English or Hindi
- **Index a new project** — provide a path, RepoMind indexes all source files
- **View projects** — table of all indexed projects with stats
- **Remove a project** — deletes vectors from Qdrant and config entry

### `repomind status`

Check health of all services at a glance:

```
  Services
  ┌─────────┬──────────────────────┬─────────────────┐
  │ Service │ Address              │ Status          │
  ├─────────┼──────────────────────┼─────────────────┤
  │ Ollama  │ http://localhost:... │ ✓  Running      │
  │ Qdrant  │ localhost:6333       │ ✓  Running      │
  └─────────┴──────────────────────┴─────────────────┘
```

---

## How It Works

```
Your Code
    │
    ▼
  Indexer          Walk repo → skip ignored dirs → chunk files (400 tokens, 80 overlap)
    │
    ▼
  Embedder         nomic-embed-text via Ollama → 768-dim vectors
    │
    ▼
  Qdrant           Store in collection repomind_{project} (cosine similarity)
    │
    ▼  ──── at query time ────
    │
  Embedder         Embed your question with the same model
    │
    ▼
  Retriever        Top-8 most similar chunks from Qdrant
    │
    ▼
  LLM              Build prompt with context → stream answer via Ollama
    │
    ▼
  Terminal         Streamed tokens, then source file citations
```

---

## Model Selection Guide

RepoMind auto-detects your hardware and picks the best model:

| Your Machine | Suggested Model | Quality |
|-------------|----------------|---------|
| < 8 GB RAM | `phi3.5:3.8b` | ★★☆☆☆ Lite |
| 8–16 GB RAM | `llama3.2:3b` | ★★★☆☆ Good |
| 16+ GB RAM | `llama3.1:8b` | ★★★★☆ Great |
| Apple Silicon 16GB+ | `llama3.1:8b` | ★★★★☆ Great |
| Apple Silicon 32GB+ | `llama3.3:70b` | ★★★★★ Best |
| NVIDIA GPU ≥ 8GB VRAM | `llama3.1:8b` | ★★★★☆ Great |
| NVIDIA GPU ≥ 24GB VRAM | `llama3.3:70b` | ★★★★★ Best |

> **Hindi support:** `llama3.1:8b` and above handle Hindi well. Lighter models (3B and below) have limited Hindi understanding.

---

## Project Layout

```
repomind/
├── src/                     ← Package root (maps to repomind.*)
│   ├── cli/                 ← Commands: main, install, chat
│   ├── config/              ← Settings model + persistence
│   ├── llm/                 ← Ollama LLM client (generate, pull, status)
│   ├── embedder/            ← Embedding client (nomic-embed-text)
│   ├── indexer/             ← File traversal + token-based chunking
│   ├── retriever/           ← Qdrant vector store + RAG pipeline
│   └── utils/               ← Display (Rich), system detection, safety, session
├── docker/                  ← Qdrant docker-compose (bundled)
├── docs/                    ← Architecture docs
├── sessions/                ← (gitignored) session log output during dev
├── tests/                   ← pytest unit tests
└── scripts/install.sh       ← curl-pipe bootstrap script
```

---

## Session Logs

After every chat session, RepoMind writes a structured markdown log to `~/.repomind/sessions/`:

```
~/.repomind/sessions/
  2024-01-15_14-32-07.md
  2024-01-16_09-45-22.md
```

Each log contains:
- Session summary (agent, duration, question count)
- List of projects queried and indexed
- Full Q&A transcript

---

## Privacy

RepoMind is designed from the ground up to keep your code private:

- **No cloud calls** — Ollama and Qdrant both run on `localhost`
- **No telemetry** — zero analytics, no crash reporting, nothing leaves your machine
- **No accounts** — no sign-up, no API keys
- **Vectors are local** — stored in a Docker volume on your machine
- **Config is local** — `~/.repomind/config.json`, readable only by you

---

## Development

```bash
git clone https://github.com/manishdashsharma/RepoMind
cd repomind
uv sync              # install deps + package in editable mode
uv run repomind install
uv run repomind
```

### Running tests

```bash
uv run pytest tests/ -v
```

### Linting

```bash
uv run ruff check src/
uv run ruff format src/
uv run mypy src/
```

---

## Contributing

Contributions are very welcome! This is a community project.

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/your-feature`)
3. Write tests for your changes
4. Run `uv run ruff check src/ && uv run pytest tests/`
5. Open a pull request

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting your first PR.

### Ideas for contributions

- [ ] Incremental reindexing (only re-embed changed files)
- [ ] `repomind config` command to update settings from CLI
- [ ] Support for remote Ollama / Qdrant instances
- [ ] Export session logs to different formats
- [ ] File-level filtering when asking questions
- [ ] VS Code extension

---

## FAQ

**Q: How is this different from GitHub Copilot or Cursor?**  
A: Those send your code to external servers. RepoMind runs entirely on your machine — your code never leaves.

**Q: Does it work on Windows?**  
A: Not officially tested yet. Docker and Ollama support Windows, so it should work. PRs welcome!

**Q: Can I use a different LLM provider?**  
A: Currently Ollama-only. Support for other local providers is on the roadmap.

**Q: How do I update the model after install?**  
A: Run `repomind install` again and choose a different model when prompted.

**Q: My Hindi answers aren't great. What model should I use?**  
A: Use `llama3.1:8b` or larger. Smaller models have limited multilingual support.

---

## Author

<table>
  <tr>
    <td align="center">
      <a href="https://www.manishdashsharma.com/">
        <b>Manish Dash Sharma</b>
      </a>
      <br />
      <sub>Senior Software Engineer</sub>
      <br /><br />
      Architecting AI-powered systems that scale.<br />
      From GenAI integrations to full-stack solutions —<br />
      turning complex problems into elegant code.
      <br /><br />
      <a href="https://www.manishdashsharma.com/">🌐 Website</a> ·
      <a href="https://github.com/manishdashsharma">GitHub</a>
    </td>
  </tr>
</table>

---

## License

MIT © [Manish Dash Sharma](https://www.manishdashsharma.com/)

---

<div align="center">

Built with ❤️ for the developer community · 100% local · 100% yours

**[⭐ Star this repo](https://github.com/manishdashsharma/RepoMind)** if RepoMind helps you understand code faster!

</div>
