# Zeocloud — Architecture

## Overview

Zeocloud is a local-first RAG (Retrieval Augmented Generation) system for codebases. Every component runs on the developer's machine — no cloud, no telemetry.

```
Developer
   │
   ▼
zeocloud (CLI)
   │
   ├── zeocloud install       ← One-time setup wizard
   │     ├── Detect hardware (CPU/RAM/GPU)
   │     ├── Suggest Ollama model
   │     ├── Pull models via Ollama
   │     └── Start Qdrant in Docker
   │
   └── zeocloud               ← Main interactive loop
         ├── Name your agent
         ├── Index a project  ─────────────────────────────┐
         │     ├── Walk repo (respects .gitignore)          │
         │     ├── Chunk files (400 tokens, 80 overlap)     │
         │     ├── Embed each chunk (nomic-embed-text)      │
         │     └── Store in Qdrant collection               │
         │                                                  │
         └── Ask a question   ──────────────────────────────┘
               ├── Embed question
               ├── Cosine similarity search in Qdrant
               ├── Build prompt with top-8 chunks
               └── Stream answer from Ollama LLM
```

## Components

### CLI Layer (`src/cli/`)

| File | Responsibility |
|------|---------------|
| `main.py` | Typer app root, agent naming, routes to install/chat |
| `install.py` | Setup wizard — hardware detection, model pull, Qdrant start |
| `chat.py` | Interactive Q&A loop, project indexing, session saving |

### Core Layer (`src/core/`)

| File | Responsibility |
|------|---------------|
| `indexer.py` | Repo traversal, language detection, token-based chunking |
| `vector_store.py` | Qdrant CRUD — collections per project, cosine search |
| `rag.py` | Full pipeline: embed → search → prompt → stream generate |

### Utils (`src/utils/`)

| File | Responsibility |
|------|---------------|
| `display.py` | All Rich UI — banner, spinners, tables, panels, progress |
| `system.py` | Hardware detection, model recommendation matrix |
| `ollama_client.py` | httpx-based Ollama REST wrapper |

### Config (`src/config/`)

| File | Responsibility |
|------|---------------|
| `settings.py` | Pydantic config model, read/write `~/.zeocloud/config.json` |

## Data Flow — Indexing

```
Repo Path
   │
   ▼
indexer.walk()          # respects .gitignore, skips node_modules etc.
   │
   ▼
indexer._chunk()        # 400 token chunks, 80 token overlap, line numbers tracked
   │
   ▼
ollama.embed()          # nomic-embed-text → 768-dim float vector per chunk
   │
   ▼
vector_store.upsert()   # stored in Qdrant collection "zeocloud_{project_name}"
```

## Data Flow — Q&A

```
User Question (English or Hindi)
   │
   ▼
ollama.embed(question)      # same nomic-embed-text model
   │
   ▼
vector_store.search()       # cosine similarity, top-8 chunks
   │
   ▼
rag._build_prompt()         # inject chunks as context + user question
   │
   ▼
ollama.generate_stream()    # LLM answers with stream, agent personality injected via system prompt
   │
   ▼
Terminal (streamed tokens)
   │
   ▼
Sources listed              # file paths + line numbers
```

## Storage

| What | Where |
|------|-------|
| Config | `~/.zeocloud/config.json` |
| Session logs | `~/.zeocloud/sessions/{date}.md` |
| Qdrant data | Docker volume `zeocloud_qdrant_data` |
| Qdrant compose | `~/.zeocloud/docker/docker-compose.yml` |

## Model Selection Matrix

| RAM | Chip | Suggested Model | Quality |
|-----|------|----------------|---------|
| < 8 GB | Any | `phi3.5:3.8b` | ★★☆☆☆ Lite |
| 8–16 GB | x86 | `llama3.2:3b` | ★★★☆☆ Good |
| 16+ GB | x86 | `llama3.1:8b` | ★★★★☆ Great |
| 16+ GB | Apple Silicon | `llama3.1:8b` | ★★★★☆ Great |
| 32+ GB | Apple Silicon | `llama3.3:70b` | ★★★★★ Best |
| NVIDIA ≥ 8GB VRAM | Any | `llama3.1:8b` | ★★★★☆ Great |
| NVIDIA ≥ 24GB VRAM | Any | `llama3.3:70b` | ★★★★★ Best |

Embedding model is always `nomic-embed-text` (dim=768) regardless of LLM choice.

## Chunking Strategy

- **Tokenizer**: `tiktoken` with `cl100k_base` encoding
- **Chunk size**: 400 tokens
- **Overlap**: 80 tokens (ensures continuity across boundaries)
- **Metadata per chunk**: `file_path`, `language`, `start_line`, `end_line`, `chunk_id`
- **Max file size**: 1 MB (larger files skipped)
- **Encoding fallback**: `utf-8` → `utf-8-sig` → `latin-1`

## Security Model

- Zero network calls to any external service
- Ollama serves on `localhost:11434`
- Qdrant serves on `localhost:6333` (Docker, not exposed externally)
- Config stored in `~/.zeocloud/` with default OS permissions
- No credentials, no API keys, no accounts required
