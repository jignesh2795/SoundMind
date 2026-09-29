from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AudioAnalysis:
    duration_seconds: float | None
    sample_rate: int | None
    channels: int | None
    tempo_bpm: float | None
    rms_energy: float | None
    spectral_centroid: float | None
    spectral_bandwidth: float | None
    spectral_rolloff: float | None
    zero_crossing_rate: float | None
    mfcc: tuple[float, ...]
    chroma: tuple[float, ...]
    analyzed_seconds: float | None = None
    analysis_mode: str = "bounded"


def _load_librosa():
    try:
        import librosa
    except ImportError as exc:
        raise RuntimeError("Audio analysis requires librosa") from exc
    return librosa


def analyze_audio(
    path: Path,
    *,
    max_analysis_seconds: float = 180.0,
    analysis_offset_seconds: float = 0.0,
) -> AudioAnalysis:
    if max_analysis_seconds <= 0:
        raise ValueError("max_analysis_seconds must be positive")
    if analysis_offset_seconds < 0:
        raise ValueError("analysis_offset_seconds must be non-negative")

    librosa = _load_librosa()
    samples, sample_rate = librosa.load(
        path,
        sr=None,
        mono=True,
        offset=analysis_offset_seconds,
        duration=max_analysis_seconds,
    )
    import numpy as np

    analyzed = float(len(samples) / sample_rate) if sample_rate else 0.0
    if samples.size == 0:
        return AudioAnalysis(
            None, int(sample_rate), 1, None, None, None, None, None, None,
            (), (), 0.0,
        )

    rms = librosa.feature.rms(y=samples)[0]
    centroid = librosa.feature.spectral_centroid(y=samples, sr=sample_rate)[0]
    bandwidth = librosa.feature.spectral_bandwidth(y=samples, sr=sample_rate)[0]
    rolloff = librosa.feature.spectral_rolloff(y=samples, sr=sample_rate)[0]
    zcr = librosa.feature.zero_crossing_rate(y=samples)[0]
    mfcc = librosa.feature.mfcc(y=samples, sr=sample_rate, n_mfcc=13)
    chroma = librosa.feature.chroma_stft(y=samples, sr=sample_rate)
    tempo, _ = librosa.beat.beat_track(y=samples, sr=sample_rate)

    scalar = lambda values: float(np.mean(values))
    tempo_value = float(np.asarray(tempo).reshape(-1)[0]) if np.size(tempo) else None

    return AudioAnalysis(
        None,
        int(sample_rate),
        1,
        tempo_value,
        scalar(rms),
        scalar(centroid),
        scalar(bandwidth),
        scalar(rolloff),
        scalar(zcr),
        tuple(float(x) for x in np.mean(mfcc, axis=1)),
        tuple(float(x) for x in np.mean(chroma, axis=1)),
        analyzed,
        "bounded",
    )
