"""M10.3 context-aware composition of the established music pipeline."""

from dataclasses import dataclass, replace
from datetime import datetime

from soundmind.flow import EndToEndCandidate, EndToEndRequest, EndToEndResult
from soundmind.intent import parse_intent
from soundmind.preferences.contextual import ContextualPreferenceScorer
from soundmind.preferences.models import ListeningEvent
from soundmind.preferences.novelty import ContextualNoveltyScorer
from soundmind.recommendation.fusion import rank_candidates
from soundmind.recommendation.intent_retrieval import IntentRetrievalEngine
from soundmind.recommendation.learned_retrieval import LearnedRetrievalEngine
from soundmind.sequence import SequenceCandidate, SequenceRequest, sequence_playlist


@dataclass(frozen=True)
class ContextAwareMusicFlow:
    """Compose contextual preference, novelty, learned retrieval, ranking, and sequencing."""

    retrieval: IntentRetrievalEngine | None = None
    learned: LearnedRetrievalEngine | None = None
    preference: ContextualPreferenceScorer | None = None
    novelty: ContextualNoveltyScorer | None = None

    def __post_init__(self) -> None:
        if self.retrieval is None:
            object.__setattr__(self, "retrieval", IntentRetrievalEngine())
        if self.preference is None:
            object.__setattr__(self, "preference", ContextualPreferenceScorer())
        if self.novelty is None:
            object.__setattr__(self, "novelty", ContextualNoveltyScorer())

    def run(
        self,
        request: EndToEndRequest,
        *,
        events: list[ListeningEvent],
        context: str,
        now: datetime,
        seed_track_id: str | None = None,
    ) -> EndToEndResult:
        if not context.strip():
            raise ValueError("context must be non-empty")

        materialized = tuple(request.candidates)
        seen: set[str] = set()
        for candidate in materialized:
            track_id = candidate.intent_candidate.track_id
            if track_id in seen:
                raise ValueError(f"duplicate track_id: {track_id!r}")
            seen.add(track_id)

        candidates = materialized
        if seed_track_id is not None:
            if self.learned is None:
                raise ValueError("learned retrieval is required when seed_track_id is supplied")
            enriched = self.learned.enrich(
                seed_track_id,
                (candidate.intent_candidate for candidate in materialized),
                limit=max(1, request.limit),
            )
            by_id = {candidate.track_id: candidate for candidate in enriched}
            candidates = tuple(
                replace(
                    candidate,
                    intent_candidate=by_id[candidate.intent_candidate.track_id],
                )
                for candidate in materialized
                if candidate.intent_candidate.track_id != seed_track_id
            )

        intent = parse_intent(request.text)
        signals = self.retrieval.enrich_many(
            intent,
            (candidate.intent_candidate for candidate in candidates),
        )
        contextual_preference = self.preference.score_events(
            events,
            context=context,
            now=now,
        )
        contextual_novelty = self.novelty.score_events(
            events,
            context=context,
            now=now,
        )

        enriched_signals = tuple(
            replace(
                signal,
                preference_score=contextual_preference.get(signal.track_id, 0.0),
                novelty_score=contextual_novelty.get(signal.track_id, 1.0),
            )
            for signal in signals
        )
        ranked = tuple(
            rank_candidates(
                enriched_signals,
                weights=request.weights,
                limit=request.limit,
            )
        )

        by_track_id = {
            candidate.intent_candidate.track_id: candidate for candidate in candidates
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
