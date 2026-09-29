"""M8 composition of learned audio retrieval with the existing M5 flow."""

from dataclasses import replace

from soundmind.flow import (
    EndToEndMusicFlow,
    EndToEndRequest,
    EndToEndResult,
)
from soundmind.recommendation.learned_retrieval import LearnedRetrievalEngine


class LearnedEndToEndMusicFlow:
    """Run M8 learned similarity before the unchanged M5 pipeline."""

    def __init__(
        self,
        learned: LearnedRetrievalEngine,
        flow: EndToEndMusicFlow | None = None,
    ) -> None:
        self._learned = learned
        self._flow = flow or EndToEndMusicFlow()

    def run(
        self,
        request: EndToEndRequest,
        *,
        seed_track_id: str,
    ) -> EndToEndResult:
        enriched = self._learned.enrich(
            seed_track_id,
            (candidate.intent_candidate for candidate in request.candidates),
            limit=max(1, request.limit),
        )
        enriched_by_id = {candidate.track_id: candidate for candidate in enriched}
        candidates = tuple(
            replace(
                candidate,
                intent_candidate=enriched_by_id[candidate.intent_candidate.track_id],
            )
            for candidate in request.candidates
            if candidate.intent_candidate.track_id != seed_track_id
        )
        return self._flow.run(replace(request, candidates=candidates))
