from __future__ import annotations

from unittest.mock import MagicMock

from zeocloud.retriever.pipeline import RAGPipeline
from zeocloud.retriever.qdrant import SearchResult


def _make_result(file: str = "app.py", score: float = 0.9) -> SearchResult:
    return SearchResult(
        file_path=file,
        language="python",
        content="def hello():\n    return 'world'\n",
        start_line=1,
        end_line=3,
        score=score,
    )


def _make_pipeline() -> tuple[RAGPipeline, MagicMock, MagicMock, MagicMock]:
    llm = MagicMock()
    embedder = MagicMock()
    store = MagicMock()
    pipeline = RAGPipeline(
        llm=llm,
        embedder=embedder,
        store=store,
        model="llama3.2:3b",
        agent_name="buddy",
    )
    return pipeline, llm, embedder, store


class TestBuildPrompt:
    def test_includes_question(self) -> None:
        pipeline, _, embedder, store = _make_pipeline()
        results = [_make_result()]
        prompt = pipeline._build_prompt("What does hello() do?", results)
        assert "What does hello() do?" in prompt

    def test_includes_file_path(self) -> None:
        pipeline, _, embedder, store = _make_pipeline()
        results = [_make_result("src/utils.py")]
        prompt = pipeline._build_prompt("explain", results)
        assert "src/utils.py" in prompt

    def test_includes_code_block(self) -> None:
        pipeline, _, embedder, store = _make_pipeline()
        results = [_make_result()]
        prompt = pipeline._build_prompt("explain", results)
        assert "```python" in prompt

    def test_multiple_results_all_included(self) -> None:
        pipeline, _, embedder, store = _make_pipeline()
        results = [_make_result("a.py"), _make_result("b.py")]
        prompt = pipeline._build_prompt("test", results)
        assert "a.py" in prompt
        assert "b.py" in prompt


class TestRAGPipeline:
    def test_returns_no_results_message_when_empty(self) -> None:
        pipeline, llm, embedder, store = _make_pipeline()
        embedder.embed.return_value = [0.1] * 768
        store.search.return_value = []

        tokens = list(pipeline.ask("myproject", "where is auth?"))
        full = "".join(tokens)
        assert "couldn't find" in full.lower() or "no relevant" in full.lower()

    def test_streams_tokens_when_results_found(self) -> None:
        pipeline, llm, embedder, store = _make_pipeline()
        embedder.embed.return_value = [0.1] * 768
        store.search.return_value = [_make_result()]
        llm.generate_stream.return_value = iter(["The ", "function ", "returns ", "world."])

        tokens = list(pipeline.ask("myproject", "what does hello return?"))
        combined = "".join(tokens)
        assert "world" in combined

    def test_sources_appended_after_answer(self) -> None:
        pipeline, llm, embedder, store = _make_pipeline()
        embedder.embed.return_value = [0.1] * 768
        store.search.return_value = [_make_result("models/user.py")]
        llm.generate_stream.return_value = iter(["answer"])

        tokens = list(pipeline.ask("myproject", "question"))
        combined = "".join(tokens)
        assert "models/user.py" in combined
        assert "Sources" in combined

    def test_agent_name_in_system_prompt(self) -> None:
        pipeline, llm, embedder, store = _make_pipeline()
        embedder.embed.return_value = [0.1] * 768
        store.search.return_value = [_make_result()]
        llm.generate_stream.return_value = iter(["ok"])

        list(pipeline.ask("myproject", "test"))

        call_kwargs = llm.generate_stream.call_args
        system_arg = call_kwargs[1].get("system") or call_kwargs[0][2]
        assert "buddy" in system_arg
