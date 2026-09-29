"""Read-only catalog adapter for the M5 end-to-end music flow."""

from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from soundmind.flow import EndToEndCandidate
from soundmind.recommendation.fusion import CandidateSignals
from soundmind.recommendation.intent_retrieval import IntentCandidate
from soundmind.storage.models import TrackRow


@dataclass(frozen=True)
class CatalogCandidate:
    """A catalog row converted into evidence consumed by M5."""

    candidate: EndToEndCandidate
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


def candidate_from_row(row: TrackRow) -> CatalogCandidate:
    """Map stored catalog evidence without inferring unavailable semantics."""
    intent_candidate = IntentCandidate(
        track_id=row.track_id,
        genres=_genre_values(row),
        energy=_energy(row),
        base_signals=CandidateSignals(row.track_id),
    )
    return CatalogCandidate(
        candidate=EndToEndCandidate(
            intent_candidate=intent_candidate,
            tempo_bpm=row.tempo_bpm,
        ),
        title=row.title,
        artist=row.artist,
        album=row.album,
    )


class CatalogCandidateRepository:
    """Read active catalog tracks and adapt them to M5 candidates."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def candidates(self, *, limit: int | None = None) -> list[CatalogCandidate]:
        statement = select(TrackRow).where(TrackRow.status == "active").order_by(TrackRow.track_id)
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
