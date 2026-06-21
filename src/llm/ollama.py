from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any

import httpx


class OllamaError(Exception):
    pass


class OllamaClient:
    def __init__(
        self,
        host: str = "http://localhost:11434",
        timeout: float = 300.0,
    ) -> None:
        self._base = host.rstrip("/")
        self._timeout = timeout

    def is_running(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                return client.get(f"{self._base}/api/tags").status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError):
            return False

    def list_models(self) -> list[str]:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{self._base}/api/tags")
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]

    def has_model(self, model: str) -> bool:
        try:
            available = self.list_models()
        except Exception:
            return False
        name = model.split(":")[0]
        tag = model.split(":")[1] if ":" in model else "latest"
        for m in available:
            m_name = m.split(":")[0]
            m_tag = m.split(":")[1] if ":" in m else "latest"
            if m_name == name and (tag == "latest" or m_tag.startswith(tag)):
                return True
        return False

    def pull_model(self, model: str) -> Generator[dict[str, Any], None, None]:
        with (
            httpx.Client(timeout=self._timeout) as client,
            client.stream(
                "POST",
                f"{self._base}/api/pull",
                json={"name": model, "stream": True},
            ) as resp,
        ):
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    data: dict[str, Any] = json.loads(line)
                    yield data
                    if data.get("status") == "success":
                        return
                except json.JSONDecodeError:
                    continue

    def embed(self, model: str, text: str) -> list[float]:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{self._base}/api/embeddings",
                json={"model": model, "prompt": text},
            )
            resp.raise_for_status()
            data = resp.json()
            embedding: list[float] = data.get("embedding") or []
            if not embedding:
                raise OllamaError(f"Empty embedding returned by model '{model}'")
            return embedding

    def get_embed_dim(self, model: str) -> int:
        return len(self.embed(model, "ping"))

    def generate_stream(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
    ) -> Generator[str, None, None]:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_ctx": 4096,
            },
        }
        if system:
            payload["system"] = system

        with (
            httpx.Client(timeout=self._timeout) as client,
            client.stream("POST", f"{self._base}/api/generate", json=payload) as resp,
        ):
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    token: str = data.get("response", "")
                    if token:
                        yield token
                    if data.get("done"):
                        return
                except json.JSONDecodeError:
                    continue


LLMClient = OllamaClient
