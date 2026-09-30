"""Persistent NumPy vector index with integrity-checked publication."""

import json
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class SimilarityResult:
    track_id: str
    score: float


class NumpyVectorIndex:
    def __init__(self, path: Path, dimension: int):
        if dimension <= 0:
            raise ValueError("dimension must be positive")
        self.path = path
        self.dimension = dimension
        self.ids_path = path.with_suffix(".ids.npy")
        self.vectors_path = path.with_suffix(".vectors.npy")
        self.integrity_path = path.with_suffix(".integrity.json")

    def save(self, track_ids, vectors):
        matrix = np.asarray(vectors, dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[1] != self.dimension:
            raise ValueError(f"Expected matrix shape (n, {self.dimension}), got {matrix.shape}")
        if len(track_ids) != matrix.shape[0]:
            raise ValueError("track_ids and vectors must contain the same number of rows")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        tv = self.vectors_path.with_suffix(".tmp.npy")
        ti = self.ids_path.with_suffix(".tmp.npy")
        tm = self.integrity_path.with_suffix(".tmp.json")

        np.save(tv, matrix)
        np.save(ti, np.asarray(track_ids, dtype=str))

        manifest = {
            "version": 1,
            "dimension": self.dimension,
            "track_count": len(track_ids),
            "ids_signature": _file_signature(ti),
            "vectors_signature": _file_signature(tv),
        }
        tm.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

        os.replace(tv, self.vectors_path)
        os.replace(ti, self.ids_path)
        os.replace(tm, self.integrity_path)

    def load(self):
        if not self.ids_path.exists() or not self.vectors_path.exists():
            return [], np.empty((0, self.dimension), dtype=np.float32)
        if not self.integrity_path.exists():
            raise ValueError(
                "Persisted vector index integrity metadata is missing; rebuild the index"
            )

        manifest = _load_integrity_manifest(self.integrity_path)
        _validate_integrity_manifest(manifest, dimension=self.dimension)

        if _file_signature(self.ids_path) != manifest["ids_signature"]:
            raise ValueError("Persisted vector index failed integrity validation; rebuild the index")
        if _file_signature(self.vectors_path) != manifest["vectors_signature"]:
            raise ValueError("Persisted vector index failed integrity validation; rebuild the index")

        ids = np.load(self.ids_path, allow_pickle=False).astype(str).tolist()
        vectors = np.asarray(
            np.load(self.vectors_path, allow_pickle=False),
            dtype=np.float32,
        )
        if vectors.ndim != 2 or vectors.shape[1] != self.dimension:
            raise ValueError("Persisted vector index has an unexpected dimension")
        if len(ids) != vectors.shape[0]:
            raise ValueError("Persisted vector index is inconsistent")
        if len(ids) != manifest["track_count"]:
            raise ValueError("Persisted vector index integrity metadata is inconsistent")
        return ids, vectors

    def search(self, query, *, limit=10):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be positive")
        ids, vectors = self.load()
        if not ids:
            return []
        q = np.asarray(query, dtype=np.float32)
        norm = float(np.linalg.norm(q))
        if q.shape != (self.dimension,) or norm == 0 or not np.isfinite(norm):
            return []
        scores = vectors @ (q / norm)
        order = np.argsort(-scores)[:limit]
        return [SimilarityResult(ids[int(i)], float(scores[int(i)])) for i in order]


def _file_signature(path: Path) -> dict[str, int]:
    stat = path.stat()
    return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def _load_integrity_manifest(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(
            "Persisted vector index integrity metadata is invalid; rebuild the index"
        ) from exc
    if not isinstance(value, dict):
        raise ValueError(
            "Persisted vector index integrity metadata is invalid; rebuild the index"
        )
    return value


def _validate_integrity_manifest(
    manifest: dict[str, object],
    *,
    dimension: int,
) -> None:
    if manifest.get("version") != 1:
        raise ValueError("Persisted vector index integrity version is unsupported; rebuild the index")
    if manifest.get("dimension") != dimension:
        raise ValueError(
            "Persisted vector index integrity dimension does not match; rebuild the index"
        )

    track_count = manifest.get("track_count")
    if isinstance(track_count, bool) or not isinstance(track_count, int) or track_count < 0:
        raise ValueError("Persisted vector index integrity count is invalid; rebuild the index")

    for key in ("ids_signature", "vectors_signature"):
        value = manifest.get(key)
        if not isinstance(value, dict):
            raise ValueError(  # noqa: TRY004
                "Persisted vector index integrity metadata is invalid; rebuild the index"
            )
        size = value.get("size")
        mtime_ns = value.get("mtime_ns")
        if (
            isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
            or isinstance(mtime_ns, bool)
            or not isinstance(mtime_ns, int)
            or mtime_ns < 0
        ):
            raise ValueError(
                "Persisted vector index integrity metadata is invalid; rebuild the index"
            )
