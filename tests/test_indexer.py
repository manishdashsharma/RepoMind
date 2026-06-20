from __future__ import annotations

from pathlib import Path

import tiktoken

from repomind.indexer.indexer import (
    _chunk_file,
    _detect_language,
    _read_safe,
    count_indexable_files,
    index_repository,
)


def _enc() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


class TestLanguageDetection:
    def test_python(self) -> None:
        assert _detect_language(Path("app.py")) == "python"

    def test_typescript(self) -> None:
        assert _detect_language(Path("component.tsx")) == "typescript"

    def test_unknown_extension(self) -> None:
        assert _detect_language(Path("file.xyz")) is None

    def test_dockerfile_by_name(self) -> None:
        assert _detect_language(Path("Dockerfile")) == "dockerfile"


class TestChunking:
    def test_small_file_is_one_chunk(self) -> None:
        content = "def hello():\n    return 'world'\n"
        chunks = _chunk_file(content, "app.py", "python", _enc())
        assert len(chunks) == 1
        assert chunks[0]["file_path"] == "app.py"
        assert chunks[0]["language"] == "python"
        assert chunks[0]["start_line"] == 1

    def test_chunk_ids_are_unique(self) -> None:
        lines = [f"line {i}\n" for i in range(200)]
        content = "".join(lines)
        chunks = _chunk_file(content, "big.py", "python", _enc())
        ids = [c["chunk_id"] for c in chunks]
        assert len(ids) == len(set(ids))

    def test_empty_content_produces_no_chunks(self) -> None:
        chunks = _chunk_file("   \n\n\n", "empty.py", "python", _enc())
        assert chunks == []

    def test_overlap_means_last_line_of_prev_in_next(self) -> None:
        lines = [
            f"variable_{i:04d} = 'long_string_value_for_test_{i:04d}'  # comment {i}\n"
            for i in range(150)
        ]
        content = "".join(lines)
        chunks = _chunk_file(content, "f.py", "python", _enc())
        assert len(chunks) >= 2
        prev_end = chunks[0]["end_line"]
        next_start = chunks[1]["start_line"]
        assert int(str(next_start)) <= int(str(prev_end))


class TestFileReading:
    def test_reads_utf8(self, tmp_path: Path) -> None:
        f = tmp_path / "hello.py"
        f.write_text("print('नमस्ते')\n", encoding="utf-8")
        content = _read_safe(f)
        assert content is not None
        assert "नमस्ते" in content

    def test_skips_large_file(self, tmp_path: Path) -> None:
        f = tmp_path / "large.py"
        f.write_bytes(b"x" * (2 * 1024 * 1024))
        assert _read_safe(f) is None


class TestIndexRepository:
    def test_counts_indexable_files(self, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text("pass\n")
        (tmp_path / "style.css").write_text("body {}\n")
        (tmp_path / "README.md").write_text("# Hi\n")
        (tmp_path / "binary.bin").write_bytes(b"\x00\x01\x02")
        assert count_indexable_files(tmp_path) == 3

    def test_skips_node_modules(self, tmp_path: Path) -> None:
        nm = tmp_path / "node_modules" / "lodash"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("module.exports = {}\n")
        (tmp_path / "app.py").write_text("pass\n")
        assert count_indexable_files(tmp_path) == 1

    def test_respects_gitignore(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("secret.py\n")
        (tmp_path / "app.py").write_text("pass\n")
        (tmp_path / "secret.py").write_text("password = 'hunter2'\n")
        files_indexed = {c["file_path"] for c in index_repository(tmp_path)}
        assert "app.py" in files_indexed
        assert "secret.py" not in files_indexed

    def test_index_returns_chunks_with_metadata(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("def main():\n    pass\n")
        chunks = index_repository(tmp_path)
        assert len(chunks) == 1
        assert chunks[0]["language"] == "python"
        assert "chunk_id" in chunks[0]
        assert "content" in chunks[0]
