"""Read-only catalog adapter for the M5 end-to-end music flow."""

import json
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from soundmind.dna import MusicDNA, normalized_brightness
from soundmind.flow import EndToEndCandidate
from soundmind.recommendation.fusion import CandidateSignals
from soundmind.recommendation.intent_retrieval import IntentCandidate
from soundmind.storage.models import TrackRow


@dataclass(frozen=True)
class CatalogCandidate:
    """A catalog row converted into evidence consumed by M5."""

    candidate: EndToEndCandidate
    music_dna: MusicDNA
    title: str | None = None
    artist: str | None = None
    album: str | None = None


def _energy(row: TrackRow) -> float | None:
    if row.rms_energy is None:
        return None
    return max(0.0, min(1.0, float(row.rms_energy)))


def _genre_values(row: TrackRow) -> tuple[str, ...]:
    if not row.genre:
        return ()
    return tuple(
        sorted({value.strip().lower() for value in row.genre.split(",") if value.strip()})
    )


def _vector(value: str | None) -> tuple[float, ...]:
    if not value:
        return ()
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return ()
    if not isinstance(parsed, list):
        return ()
    try:
        return tuple(float(item) for item in parsed)
    except (TypeError, ValueError):
        return ()


def music_dna_from_row(row: TrackRow) -> MusicDNA:
    """Build measured Music DNA without inferring unavailable semantics."""
    return MusicDNA(
        tempo_bpm=row.tempo_bpm,
        energy=_energy(row),
        brightness=normalized_brightness(row.spectral_centroid, row.sample_rate),
        spectral_bandwidth=row.spectral_bandwidth,
        spectral_rolloff=row.spectral_rolloff,
        zero_crossing_rate=row.zero_crossing_rate,
        mfcc=_vector(row.mfcc_json),
        chroma=_vector(row.chroma_json),
    )


def candidate_from_row(row: TrackRow) -> CatalogCandidate:
    """Map stored catalog evidence without inferring unavailable semantics."""
    dna = music_dna_from_row(row)
    intent_candidate = IntentCandidate(
        track_id=row.track_id,
        genres=_genre_values(row),
        energy=dna.energy,
        base_signals=CandidateSignals(row.track_id),
    )
    return CatalogCandidate(
        candidate=EndToEndCandidate(
            intent_candidate=intent_candidate,
            tempo_bpm=dna.tempo_bpm,
            brightness=dna.brightness,
        ),
        music_dna=dna,
        title=row.title,
        artist=row.artist,
        album=row.album,
    )


class CatalogCandidateRepository:
    """Read active catalog tracks and adapt them to M5 candidates."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def candidates(self, *, limit: int | None = None) -> list[CatalogCandidate]:
        statement = (
            select(TrackRow)
            .where(TrackRow.status == "active")
            .order_by(TrackRow.track_id)
        )
        if limit is not None:
            if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
                raise ValueError("limit must be a positive integer")
            statement = statement.limit(limit)
        return [candidate_from_row(row) for row in self._session.scalars(statement)]


def end_to_end_candidates(
    rows: Iterable[TrackRow],
) -> tuple[EndToEndCandidate, ...]:
    """Adapt already-loaded catalog rows without touching the database."""
    return tuple(candidate_from_row(row).candidate for row in rows)
