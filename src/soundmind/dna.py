"""Deterministic Music DNA derived from stored catalog/audio evidence."""

from dataclasses import dataclass


def normalized_brightness(
    spectral_centroid: float | None,
    sample_rate: int | None,
) -> float | None:
    """Normalize spectral centroid against Nyquist frequency into 0..1."""
    if spectral_centroid is None or sample_rate is None or sample_rate <= 0:
        return None
    nyquist = sample_rate / 2.0
    if nyquist <= 0:
        return None
    return max(0.0, min(1.0, float(spectral_centroid) / nyquist))


@dataclass(frozen=True)
class MusicDNA:
    """Typed acoustic evidence with no inferred semantic labels."""

    tempo_bpm: float | None = None
    energy: float | None = None
    brightness: float | None = None
    spectral_bandwidth: float | None = None
    spectral_rolloff: float | None = None
    zero_crossing_rate: float | None = None
    mfcc: tuple[float, ...] = ()
    chroma: tuple[float, ...] = ()