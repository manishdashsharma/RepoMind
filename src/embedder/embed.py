from __future__ import annotations

import httpx

from zeocloud.llm.ollama import OllamaError


class EmbedClient:
    """Thin, focused client for generating text embeddings via Ollama."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        timeout: float = 60.0,
    ) -> None:
        self._base = host.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._cached_dim: int | None = None

    def embed(self, text: str) -> list[float]:
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                f"{self._base}/api/embeddings",
                json={"model": self._model, "prompt": text},
            )
            resp.raise_for_status()
            data = resp.json()
            vector: list[float] = data.get("embedding") or []
            if not vector:
                raise OllamaError(f"Empty embedding from model '{self._model}'")
            return vector

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

    @property
    def dim(self) -> int:
        if self._cached_dim is None:
            self._cached_dim = len(self.embed("hello"))
        return self._cached_dim

    @property
    def model(self) -> str:
        return self._model
