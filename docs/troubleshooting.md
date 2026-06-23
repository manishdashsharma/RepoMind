# Zeocloud — Troubleshooting

---

## Installation Issues

### `zeocloud install` fails: "Ollama is not installed"

Ollama must be installed before running `zeocloud install`.

```bash
# macOS
brew install ollama

# Or download from
# https://ollama.com/download
```

After installing, start Ollama and retry:

```bash
ollama serve
zeocloud install
```

---

### `zeocloud install` fails: "Docker is not installed" or "Docker is not running"

Install Docker Desktop from https://www.docker.com/get-started

On macOS, open Docker Desktop from Applications after installing. Wait for the whale icon to appear in the menu bar, then retry `zeocloud install`.

On Linux:
```bash
sudo systemctl start docker
```

---

### Model pull hangs or is very slow

Large models (llama3.1:8b = ~4.7 GB) take time on a slow connection. The progress bar shows download speed. If it stalls:

1. Cancel with `Ctrl+C`
2. Resume manually: `ollama pull llama3.1:8b`
3. Re-run `zeocloud install`

---

### "Qdrant did not become healthy in time"

Qdrant container didn't start within 30 seconds. Check what went wrong:

```bash
docker logs zeocloud-qdrant
```

Common causes:
- Port 6333 already in use by another process: `lsof -i :6333`
- Docker has insufficient memory allocated (increase in Docker Desktop → Settings → Resources)
- Qdrant image failed to pull: `docker pull qdrant/qdrant:v1.9.4`

---

## Runtime Issues

### "Ollama is not running"

Start Ollama before running `zeocloud`:

```bash
ollama serve
```

Or on macOS, open the Ollama app from Applications.

---

### "Qdrant is not running"

The Qdrant Docker container has stopped. Restart it:

```bash
cd ~/.zeocloud/docker
docker compose up -d
```

Or check the container status:

```bash
docker ps -a | grep zeocloud
docker start zeocloud-qdrant
```

---

### No answers / blank responses

1. Check that the model is loaded: `ollama list`
2. Try a simple test: `ollama run llama3.2:3b "hello"`
3. Ensure the project was indexed: choose option 3 (View indexed projects) in the menu
4. If the project shows 0 chunks, re-index it

---

### "No indexable source files found"

Zeocloud only indexes known source file types (Python, JS, Go, Rust, etc.). Check that:
- The path points to a directory with source code, not just config files
- The files aren't excluded by `.gitignore` in the project root
- The directory isn't in the skip list (node_modules, dist, .venv, etc.)

---

### Answers are wrong or hallucinated

- Use a larger model (`llama3.1:8b` or `llama3.3:70b`) for better accuracy
- Re-index the project after significant code changes
- Ask more specific questions: include file names or function names in your question

---

### Hindi answers are poor quality

Hindi requires at least `llama3.1:8b`. If you're on a lower model:

1. `ollama pull llama3.1:8b`
2. Edit `~/.zeocloud/config.json`: set `"model": "llama3.1:8b"`
3. Continue chatting — no re-indexing needed

---

## Indexing Issues

### Indexing is very slow

Large repositories with thousands of files take time because every chunk must be embedded via the Ollama API (one network call per batch). This is expected. Progress is shown in the progress bar.

To speed it up:
- Use Apple Silicon (M1/M2/M3) — Ollama runs much faster on unified memory
- Reduce the scope: index a subdirectory instead of the whole monorepo

---

### "Indexing … is not allowed"

Zeocloud blocks indexing of system directories (`/etc`, `/usr`, `~`, `~/.ssh`, etc.) to prevent accidental exposure of sensitive files. Index a specific project directory instead.

---

### Sensitive file warning appears

Zeocloud detected `.env`, private keys, or credentials files in your project. Options:

1. Add them to `.gitignore` (they'll be excluded automatically)
2. Confirm to index anyway — the data stays local on your machine

---

## Qdrant Issues

### Collections disappear after restart

This should not happen — Qdrant uses a named Docker volume (`zeocloud_qdrant_data`) that persists across restarts.

If it happens, the volume was deleted. Re-index your projects.

To verify the volume exists:
```bash
docker volume ls | grep zeocloud
```

---

### Port 6333 conflict

Another application is using port 6333.

```bash
lsof -i :6333
```

You can change Qdrant's port in `~/.zeocloud/docker/docker-compose.yml` (change `"6333:6333"` to `"6334:6333"`) and update `qdrant_port` in `~/.zeocloud/config.json`.

---

## Still stuck?

Open an issue on GitHub: https://github.com/manishdashsharma/Zeocloud/issues

Include:
- Output of `zeocloud status`
- Your OS and hardware (output of `uname -a` and `free -h` or `system_profiler SPHardwareDataType`)
- The full error message
