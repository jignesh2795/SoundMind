from pathlib import Path
import numpy as np
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from sqlalchemy import select

from soundmind.diagnostics import ProcessingIssue
from soundmind.embeddings.effnet import EffNetConfig, EffNetEmbedder
from soundmind.storage.models import TrackRow
from soundmind.vector.index import NumpyVectorIndex


class LearnedEmbeddingService:
    def __init__(self, session, *, model_path, index_path, max_seconds=180.0):
        self.session = session
        self.embedder = EffNetEmbedder(EffNetConfig(model_path=model_path, max_seconds=max_seconds))
        self.index = NumpyVectorIndex(index_path, self.embedder.dimension)

    def rebuild(self, *, limit=None, diagnostics: list[ProcessingIssue] | None = None):
        stmt = select(TrackRow).where(TrackRow.status == "active")
        if limit is not None:
            stmt = stmt.limit(limit)
        ids, vectors = [], []
        for row in self.session.scalars(stmt).all():
            path = self._local_path(row.source_uri)
            if path is None or not path.exists():
                if diagnostics is not None:
                    diagnostics.append(
                        ProcessingIssue(
                            "embedding", row.source_uri, "FileNotFoundError", "Local file is missing"
                        )
                    )
                continue
            try:
                vector = self.embedder.embed(path)
            except Exception as exc:  # noqa: BLE001
                if diagnostics is not None:
                    diagnostics.append(
                        ProcessingIssue("embedding", row.source_uri, type(exc).__name__, str(exc))
                    )
                continue
            vectors.append(vector)
            ids.append(row.track_id)

        matrix = (
            np.vstack(vectors).astype(np.float32)
            if vectors
            else np.empty((0, self.embedder.dimension), dtype=np.float32)
        )
        self.index.save(ids, matrix)
        return len(ids)

    def similar(self, track_id, *, limit=10):
        row = self.session.get(TrackRow, track_id)
        if row is None:
            raise KeyError(f"Track not found: {track_id}")
        path = self._local_path(row.source_uri)
        if path is None or not path.exists():
            raise FileNotFoundError(row.source_uri)
        return [
            x
            for x in self.index.search(self.embedder.embed(path), limit=limit + 1)
            if x.track_id != track_id
        ][:limit]

    @staticmethod
    def _local_path(source_uri):
        parsed = urlparse(source_uri)
        if parsed.scheme != "file":
            return None
        path = unquote(parsed.path)
        if parsed.netloc and parsed.netloc not in {"", "localhost"}:
            path = f"//{parsed.netloc}{path}"
        return Path(url2pathname(path))
