from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

_PREFIX = "repomind_"
_DEFAULT_DIM = 768


@dataclass(frozen=True)
class SearchResult:
    file_path: str
    language: str
    content: str
    start_line: int
    end_line: int
    score: float


class VectorStore:
    def __init__(self, host: str = "localhost", port: int = 6333) -> None:
        self._client = QdrantClient(host=host, port=port, timeout=30)

    def ensure_collection(self, project: str, dim: int = _DEFAULT_DIM) -> None:
        name = _col(project)
        existing = {c.name for c in self._client.get_collections().collections}
        if name not in existing:
            self._client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    def upsert(
        self,
        project: str,
        chunks: list[dict[str, object]],
        vectors: list[list[float]],
    ) -> None:
        name = _col(project)
        points = [
            PointStruct(
                id=int(str(c["chunk_id"])),
                vector=v,
                payload={
                    "file_path": c["file_path"],
                    "language": c["language"],
                    "content": c["content"],
                    "start_line": c["start_line"],
                    "end_line": c["end_line"],
                },
            )
            for c, v in zip(chunks, vectors, strict=False)
        ]
        self._client.upsert(collection_name=name, points=points)

    def search(
        self,
        project: str,
        vector: list[float],
        top_k: int = 8,
        file_filter: str | None = None,
    ) -> list[SearchResult]:
        name = _col(project)
        qfilter: Filter | None = None
        if file_filter:
            qfilter = Filter(
                must=[FieldCondition(key="file_path", match=MatchValue(value=file_filter))]
            )
        response = self._client.query_points(
            collection_name=name,
            query=vector,
            query_filter=qfilter,
            limit=top_k,
            with_payload=True,
        )
        return [
            SearchResult(
                file_path=str(h.payload["file_path"]),
                language=str(h.payload["language"]),
                content=str(h.payload["content"]),
                start_line=int(str(h.payload["start_line"])),
                end_line=int(str(h.payload["end_line"])),
                score=h.score,
            )
            for h in response.points
            if h.payload
        ]

    def delete_project(self, project: str) -> bool:
        name = _col(project)
        existing = {c.name for c in self._client.get_collections().collections}
        if name in existing:
            self._client.delete_collection(name)
            return True
        return False

    def list_projects(self) -> list[str]:
        return [
            c.name.removeprefix(_PREFIX)
            for c in self._client.get_collections().collections
            if c.name.startswith(_PREFIX)
        ]

    def count_chunks(self, project: str) -> int:
        try:
            info = self._client.get_collection(_col(project))
            return info.points_count or 0
        except Exception:
            return 0

    def is_healthy(self) -> bool:
        try:
            self._client.get_collections()
            return True
        except Exception:
            return False


def _col(project: str) -> str:
    return _PREFIX + project.lower().replace(" ", "_").replace("-", "_")
