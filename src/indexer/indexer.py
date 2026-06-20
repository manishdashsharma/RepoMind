from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pathspec
import tiktoken

_LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".scala": "scala",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".fish": "bash",
    ".md": "markdown",
    ".mdx": "markdown",
    ".txt": "text",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".ini": "ini",
    ".sql": "sql",
    ".graphql": "graphql",
    ".gql": "graphql",
    ".proto": "protobuf",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "scss",
    ".less": "css",
    ".vue": "vue",
    ".svelte": "svelte",
    ".lua": "lua",
    ".dart": "dart",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".tf": "terraform",
    ".hcl": "terraform",
    "Dockerfile": "dockerfile",
    "Makefile": "makefile",
    ".mk": "makefile",
}

_SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".svn",
        ".hg",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        "dist",
        "build",
        ".build",
        "out",
        ".out",
        ".next",
        ".nuxt",
        ".svelte-kit",
        ".venv",
        "venv",
        "env",
        ".env",
        "vendor",
        "target",
        "pkg",
        "bin",
        "obj",
        ".idea",
        ".vscode",
        "coverage",
        "htmlcov",
        ".nyc_output",
        ".terraform",
        "tmp",
        "temp",
        "cache",
        ".cache",
        "logs",
        "log",
        "migrations",
        "seeds",
    }
)

_MAX_FILE_BYTES: int = 1 * 1024 * 1024
_CHUNK_TOKENS: int = 400
_OVERLAP_TOKENS: int = 80

Chunk = dict[str, object]


def index_repository(repo_path: Path) -> list[Chunk]:
    enc = tiktoken.get_encoding("cl100k_base")
    gitignore = _load_gitignore(repo_path)
    chunks: list[Chunk] = []
    for file_path in _walk(repo_path, gitignore):
        lang = _detect_language(file_path)
        if not lang:
            continue
        content = _read_safe(file_path)
        if not content:
            continue
        rel = str(file_path.relative_to(repo_path))
        chunks.extend(_chunk_file(content, rel, lang, enc))
    return chunks


def count_indexable_files(repo_path: Path) -> int:
    gitignore = _load_gitignore(repo_path)
    return sum(1 for f in _walk(repo_path, gitignore) if _detect_language(f))


def _walk(repo_path: Path, gitignore: pathspec.PathSpec[Any] | None) -> list[Path]:
    files: list[Path] = []
    for item in repo_path.rglob("*"):
        if not item.is_file():
            continue
        parts = item.relative_to(repo_path).parts
        if any(p in _SKIP_DIRS for p in parts):
            continue
        if gitignore and gitignore.match_file(str(item.relative_to(repo_path))):
            continue
        files.append(item)
    return files


def _chunk_file(
    text: str,
    file_path: str,
    language: str,
    enc: tiktoken.Encoding,
) -> list[Chunk]:
    lines = text.splitlines(keepends=True)
    chunks: list[Chunk] = []
    current: list[str] = []
    current_tokens = 0
    start_line = 1
    chunk_idx = 0

    for line_num, line in enumerate(lines, start=1):
        line_tokens = len(enc.encode(line, disallowed_special=()))
        if current_tokens + line_tokens > _CHUNK_TOKENS and current:
            chunk_text = "".join(current)
            if chunk_text.strip():
                chunks.append(
                    _make_chunk(
                        file_path, language, chunk_text, start_line, line_num - 1, chunk_idx
                    )
                )
                chunk_idx += 1
            overlap: list[str] = []
            overlap_tokens = 0
            for ol in reversed(current):
                ot = len(enc.encode(ol, disallowed_special=()))
                if overlap_tokens + ot > _OVERLAP_TOKENS:
                    break
                overlap.insert(0, ol)
                overlap_tokens += ot
            current = overlap + [line]
            current_tokens = overlap_tokens + line_tokens
            start_line = line_num - len(overlap)
        else:
            current.append(line)
            current_tokens += line_tokens

    if current:
        chunk_text = "".join(current)
        if chunk_text.strip():
            chunks.append(
                _make_chunk(
                    file_path,
                    language,
                    chunk_text,
                    start_line,
                    start_line + len(current) - 1,
                    chunk_idx,
                )
            )
    return chunks


def _make_chunk(
    file_path: str,
    language: str,
    content: str,
    start_line: int,
    end_line: int,
    chunk_idx: int,
) -> Chunk:
    raw = hashlib.md5(f"{file_path}:{start_line}:{chunk_idx}".encode()).hexdigest()[:16]
    return {
        "chunk_id": int(raw, 16) % (2**63),
        "file_path": file_path,
        "language": language,
        "content": content,
        "start_line": start_line,
        "end_line": end_line,
        "chunk_index": chunk_idx,
    }


def _load_gitignore(repo_path: Path) -> pathspec.PathSpec[Any] | None:
    gi = repo_path / ".gitignore"
    if gi.exists():
        patterns = gi.read_text(encoding="utf-8", errors="replace").splitlines()
        return pathspec.PathSpec.from_lines("gitignore", patterns)
    return None


def _detect_language(path: Path) -> str | None:
    return _LANGUAGE_MAP.get(path.suffix.lower()) or _LANGUAGE_MAP.get(path.name)


def _read_safe(path: Path) -> str | None:
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            return None
    except OSError:
        return None
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return path.read_text(encoding=encoding, errors="replace")
        except OSError:
            return None
    return None
