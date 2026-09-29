"""Persisted semantic text index for catalog retrieval."""

import hashlib
import json
import os
from pathlib import Path
from typing import Sequence

from soundmind.recommendation.semantic_text_retrieval import (
    TextEmbeddingProvider,
    catalog_text,
)
from soundmind.storage.models import TrackRow
from soundmind.vector.index import NumpyVectorIndex


class SemanticIndexStaleError(RuntimeError):
    """Raised when the persisted semantic index does not match the catalog."""


def _catalog_fingerprint(rows: Sequence[TrackRow]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: item.track_id):
        payload = f"{row.track_id}\0{catalog_text(row)}\n".encode()
        digest.update(payload)
    return digest.hexdigest()


class PersistentSemanticTextIndex:
    """Persist and query semantic vectors derived from catalog metadata."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.manifest_path = path.with_suffix(".meta.json")

    def rebuild(
        self,
        rows: Sequence[TrackRow],
        *,
        provider: TextEmbeddingProvider,
        model_name: str,
    ) -> int:
        active_rows = sorted(
            (row for row in rows if row.status == "active"),
            key=lambda item: item.track_id,
        )
        seen: set[str] = set()
        for row in active_rows:
            if row.track_id in seen:
                raise ValueError(f"duplicate track_id: {row.track_id!r}")
            seen.add(row.track_id)

        documents = [catalog_text(row) for row in active_rows]
        if documents:
            vectors = provider.embed_documents(documents)
            if len(vectors) != len(active_rows):
                raise ValueError("embedding provider returned the wrong document count")
            dimension = len(vectors[0])
            if dimension <= 0:
                raise ValueError("embeddings must be non-empty")
            matrix = list(vectors)
        else:
            dimension = 1
            matrix = []

        index = NumpyVectorIndex(self.path, dimension)
        index.save([row.track_id for row in active_rows], matrix)

        manifest = {
            "version": 1,
            "model_name": model_name,
            "dimension": dimension,
            "catalog_fingerprint": _catalog_fingerprint(active_rows),
            "track_count": len(active_rows),
        }
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.manifest_path.with_suffix(".tmp.json")
        temp.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        os.replace(temp, self.manifest_path)
        return len(active_rows)

    def search(
        self,
        query: str,
        rows: Sequence[TrackRow],
        *,
        provider: TextEmbeddingProvider,
        model_name: str,
        limit: int = 10,
    ) -> list[tuple[str, float]]:
        if not query.strip():
            raise ValueError("query must be non-empty")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")

        manifest = self._load_manifest()
        active_rows = sorted(
            (row for row in rows if row.status == "active"),
            key=lambda item: item.track_id,
        )
        current_fingerprint = _catalog_fingerprint(active_rows)
        if manifest["model_name"] != model_name:
            raise SemanticIndexStaleError(
                "semantic index model does not match the requested model; rebuild it"
            )
        if manifest["catalog_fingerprint"] != current_fingerprint:
            raise SemanticIndexStaleError(
                "semantic index does not match the current catalog; rebuild it"
            )

        index = NumpyVectorIndex(self.path, int(manifest["dimension"]))
        query_vector = provider.embed_query(query.strip())
        results = index.search(query_vector, limit=limit)
        return [(result.track_id, result.score) for result in results]

    def _load_manifest(self) -> dict[str, object]:
        if not self.manifest_path.exists():
            raise FileNotFoundError(
                f"semantic index manifest not found: {self.manifest_path}; rebuild it first"
            )
        try:
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SemanticIndexStaleError("semantic index manifest is invalid; rebuild it") from exc
