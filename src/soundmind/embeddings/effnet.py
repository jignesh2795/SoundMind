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
    n_mels: int = 96
    n_fft: int = 512
    hop_length: int = 256
    patch_frames: int = 128
    patch_hop: int = 62

class EffNetEmbedder:
    name = "discogs-effnet-v1"
    dimension = 1280

    def __init__(self, config):
        self.config = config
        self._session = None

    def _load_session(self):
        if self._session is not None:
            return self._session
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise RuntimeError("Install optional ML dependencies with: uv sync --extra ml") from exc
        if not self.config.model_path.exists():
            raise FileNotFoundError(f"EffNet model not found: {self.config.model_path}")
        self._session = ort.InferenceSession(
            str(self.config.model_path), providers=["CPUExecutionProvider"]
        )
        return self._session

    def _patches(self, audio):
        import librosa
        mel = librosa.feature.melspectrogram(
            y=audio,
            sr=self.config.sample_rate,
            n_fft=self.config.n_fft,
            hop_length=self.config.hop_length,
            win_length=self.config.n_fft,
            n_mels=self.config.n_mels,
            power=2.0,
        )
        # EffNetDiscogs expects log-compressed mel bands with shape [batch, 128, 96].
        mel = np.log(np.maximum(mel, 1e-10)).T.astype(np.float32, copy=False)
        if mel.shape[1] != self.config.n_mels:
            raise RuntimeError(f"Unexpected mel shape: {mel.shape}")
        patches = []
        for start in range(0, max(1, mel.shape[0] - self.config.patch_frames + 1), self.config.patch_hop):
            patch = mel[start:start + self.config.patch_frames]
            if patch.shape[0] == self.config.patch_frames:
                patches.append(patch)
        if not patches:
            pad = np.zeros((self.config.patch_frames, self.config.n_mels), dtype=np.float32)
            rows = min(mel.shape[0], self.config.patch_frames)
            pad[:rows] = mel[:rows]
            patches.append(pad)
        return np.stack(patches, axis=0)

    def embed(self, path):
        import librosa
        audio, _ = librosa.load(
            path, sr=self.config.sample_rate, mono=True, duration=self.config.max_seconds
        )
        if audio.size == 0:
            return np.zeros(self.dimension, dtype=np.float32)
        session = self._load_session()
        patches = self._patches(audio)
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: patches})
        if len(outputs) < 2:
            raise RuntimeError("EffNet model did not return predictions and embeddings")
        embedding = np.asarray(outputs[1], dtype=np.float32)
        if embedding.ndim != 2 or embedding.shape[1] != self.dimension:
            raise RuntimeError(f"Unexpected embedding shape: {embedding.shape}")
        pooled = np.mean(embedding, axis=0)
        norm = float(np.linalg.norm(pooled))
        return (
            np.zeros(self.dimension, dtype=np.float32)
            if norm == 0 or not np.isfinite(norm)
            else pooled / norm
        )

def fetch_effnet_model(destination: Path, *, url=DEFAULT_MODEL_URL):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        urlretrieve(url, destination)
    return destination
