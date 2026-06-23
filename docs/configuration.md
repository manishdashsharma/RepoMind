# Zeocloud — Configuration Reference

All configuration is stored at `~/.zeocloud/config.json`. It is created automatically during `zeocloud install` and updated whenever you index a project or rename your agent.

---

## Config File Location

```
~/.zeocloud/
  config.json          ← main config
  sessions/            ← Q&A session logs (one .md per session)
  docker/
    docker-compose.yml ← Qdrant container definition
```

---

## Config Schema

```json
{
  "agent_name": "buddy",
  "model": "llama3.1:8b",
  "embed_model": "nomic-embed-text",
  "ollama_host": "http://localhost:11434",
  "qdrant_host": "localhost",
  "qdrant_port": 6333,
  "installed": true,
  "projects": {
    "my-api": {
      "name": "my-api",
      "path": "/Users/you/projects/my-api",
      "indexed_at": "2024-06-21T14:30:00",
      "file_count": 142,
      "chunk_count": 891
    }
  }
}
```

### Fields

| Field | Default | Description |
|---|---|---|
| `agent_name` | `null` | Name of your AI agent. Set on first `zeocloud` run. |
| `model` | `"llama3.2:3b"` | Ollama model used for answer generation. |
| `embed_model` | `"nomic-embed-text"` | Ollama model used for embeddings. Do not change unless you re-index all projects. |
| `ollama_host` | `"http://localhost:11434"` | Ollama API base URL. Change if you run Ollama on a custom port. |
| `qdrant_host` | `"localhost"` | Qdrant host. |
| `qdrant_port` | `6333` | Qdrant REST API port. |
| `installed` | `false` | Set to `true` after `zeocloud install` completes. |
| `projects` | `{}` | Map of indexed projects keyed by project name. |

---

## Changing the Language Model

After install, you can switch models without reinstalling:

1. Pull the new model: `ollama pull llama3.3:70b`
2. Edit `~/.zeocloud/config.json` and update the `model` field.
3. Re-index your projects (the embedding model stays the same — no re-indexing needed unless you change `embed_model`).

**Warning:** If you change `embed_model`, all Qdrant collections are incompatible with the new embedding dimensions. You must remove and re-index all projects.

---

## Supported Models

| Model | RAM Required | Quality |
|---|---|---|
| `phi3.5:3.8b` | 4 GB | Good — fast on low RAM |
| `llama3.2:3b` | 8 GB | Better — balanced |
| `llama3.1:8b` | 16 GB | Best general purpose |
| `llama3.3:70b` | 32 GB / Apple Silicon | Excellent — near GPT-4 quality |

Hindi language responses work best with `llama3.1:8b` or higher.

---

## Qdrant Collections

Each indexed project gets its own Qdrant collection named `zeocloud_{project_name}`. You can inspect them at:

```
http://localhost:6333/dashboard
```

Collections persist across restarts because Qdrant uses a named Docker volume (`zeocloud_qdrant_data`).

---

## Resetting Everything

```bash
# Remove all indexed data
docker volume rm zeocloud_qdrant_data

# Remove config
rm ~/.zeocloud/config.json

# Start fresh
zeocloud install
```
