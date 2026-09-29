from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlretrieve
import numpy as np

DEFAULT_MODEL_URL = "https://essentia.upf.edu/models/feature-extractors/discogs-effnet/discogs-effnet-bsdynamic-1.onnx"

@dataclass(frozen=True)
class EffNetConfig:
    model_path: Path
    sample_rate: int = 16000
    max_seconds: float = 180.0

class EffNetEmbedder:
    name = "discogs-effnet-v1"
    dimension = 1280
    def __init__(self, config):
        self.config = config
        self._session = None
    def _load_session(self):
        if self._session is not None: return self._session
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise RuntimeError("Install optional ML dependencies with: uv sync --extra ml") from exc
        if not self.config.model_path.exists():
            raise FileNotFoundError(f"EffNet model not found: {self.config.model_path}")
        self._session = ort.InferenceSession(str(self.config.model_path),
                                             providers=["CPUExecutionProvider"])
        return self._session
    def embed(self, path):
        import librosa
        audio, _ = librosa.load(path, sr=self.config.sample_rate, mono=True,
                                duration=self.config.max_seconds)
        if audio.size == 0: return np.zeros(self.dimension, dtype=np.float32)
        session = self._load_session()
        batch = audio.astype(np.float32, copy=False)[None, :]
        outputs = session.run(None, {session.get_inputs()[0].name: batch})
        embedding = np.squeeze(np.asarray(outputs[0], dtype=np.float32))
        pooled = embedding if embedding.ndim == 1 else np.mean(embedding.reshape(-1, embedding.shape[-1]), axis=0)
        if pooled.shape != (self.dimension,): raise RuntimeError(f"Unexpected embedding shape: {pooled.shape}")
        norm = float(np.linalg.norm(pooled))
        return np.zeros(self.dimension, dtype=np.float32) if norm == 0 or not np.isfinite(norm) else pooled / norm

def fetch_effnet_model(destination: Path, *, url=DEFAULT_MODEL_URL):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists(): urlretrieve(url, destination)
    return destination
