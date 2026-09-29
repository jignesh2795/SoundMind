from dataclasses import dataclass
from pathlib import Path
import os
import numpy as np

@dataclass(frozen=True)
class SimilarityResult:
    track_id: str
    score: float

class NumpyVectorIndex:
    def __init__(self, path: Path, dimension: int):
        self.path = path
        self.ids_path = path.with_suffix(".ids.npy")
        self.vectors_path = path.with_suffix(".vectors.npy")

    def save(self, track_ids, vectors):
        matrix = np.asarray(vectors, dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[1] != self.dimension:
            raise ValueError(f"Expected matrix shape (n, {self.dimension}), got {matrix.shape}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tv = self.vectors_path.with_suffix(".tmp.npy")
        ti = self.ids_path.with_suffix(".tmp.npy")
        np.save(tv, matrix); np.save(ti, np.asarray(track_ids, dtype=str))
        os.replace(tv, self.vectors_path); os.replace(ti, self.ids_path)

    def load(self):
        if not self.ids_path.exists() or not self.vectors_path.exists():
            return [], np.empty((0, self.dimension), dtype=np.float32)
        ids = np.load(self.ids_path, allow_pickle=False).astype(str).tolist()
        vectors = np.asarray(np.load(self.vectors_path, allow_pickle=False), dtype=np.float32)
        if len(ids) != vectors.shape[0]:
            raise ValueError("Persisted vector index is inconsistent")
        return ids, vectors

    def search(self, query, *, limit=10):
        if limit <= 0:
            raise ValueError("limit must be positive")
        ids, vectors = self.load()
        if not ids: return []
        q = np.asarray(query, dtype=np.float32)
        norm = float(np.linalg.norm(q))
        if q.shape != (self.dimension,) or norm == 0 or not np.isfinite(norm): return []
        scores = vectors @ (q / norm)
        order = np.argsort(-scores)[:limit]
        return [SimilarityResult(ids[int(i)], float(scores[int(i)])) for i in order]
