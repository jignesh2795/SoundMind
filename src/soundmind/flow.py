"""M5 orchestration from natural-language intent to ordered playlist."""

from dataclasses import dataclass

from soundmind.intent import MusicIntent, parse_intent
from soundmind.recommendation.fusion import (
    FusionWeights,
    RankedCandidate,
)
from soundmind.recommendation.intent_retrieval import (
    IntentCandidate,
    IntentRetrievalEngine,
)
from soundmind.sequence import (
    SequenceCandidate,
    SequenceItem,
    SequenceMode,
    SequenceRequest,
    sequence_playlist,
)


@dataclass(frozen=True)
class EndToEndCandidate:
    """Structured evidence supplied to the M4 and M2 boundaries."""

    intent_candidate: IntentCandidate
    tempo_bpm: float | None = None
    brightness: float | None = None


@dataclass(frozen=True)
class EndToEndRequest:
    text: str
    candidates: tuple[EndToEndCandidate, ...] | list[EndToEndCandidate]
    mode: SequenceMode = SequenceMode.SMOOTH
    seed_track_id: str | None = None
    limit: int = 10
    weights: FusionWeights | None = None


@dataclass(frozen=True)
class EndToEndResult:
    intent: MusicIntent
    ranked: tuple[RankedCandidate, ...]
    playlist: tuple[SequenceItem, ...]


class EndToEndMusicFlow:
    """Compose M3 intent, M4 retrieval, M1 ranking, and M2 sequencing."""

    def __init__(self, retrieval: IntentRetrievalEngine | None = None) -> None:
        self._retrieval = retrieval or IntentRetrievalEngine()

    def run(self, request: EndToEndRequest) -> EndToEndResult:
        seen: set[str] = set()
        for candidate in request.candidates:
            track_id = candidate.intent_candidate.track_id
            if track_id in seen:
                raise ValueError(f"duplicate track_id: {track_id!r}")
            seen.add(track_id)

        intent = parse_intent(request.text)
        ranked = tuple(
            self._retrieval.rank(
                intent,
                (candidate.intent_candidate for candidate in request.candidates),
                weights=request.weights,
                limit=request.limit,
            )
        )

        by_track_id = {
            candidate.intent_candidate.track_id: candidate
            for candidate in request.candidates
        }
        sequence_candidates = tuple(
            SequenceCandidate(
                track_id=ranked_candidate.track_id,
                base_score=ranked_candidate.score,
                energy=by_track_id[ranked_candidate.track_id].intent_candidate.energy,
                tempo_bpm=by_track_id[ranked_candidate.track_id].tempo_bpm,
                brightness=by_track_id[ranked_candidate.track_id].brightness,
                novelty_score=by_track_id[
                    ranked_candidate.track_id
                ].intent_candidate.novelty_score,
            )
            for ranked_candidate in ranked
        )
        playlist = sequence_playlist(
            SequenceRequest(
                candidates=sequence_candidates,
                mode=request.mode,
                seed_track_id=request.seed_track_id,
                limit=request.limit,
            )
        )
        return EndToEndResult(intent=intent, ranked=ranked, playlist=playlist)
