import argparse
from datetime import UTC, datetime
from pathlib import Path

from soundmind.catalog_recommendation import (
    RETRIEVAL_MODES,
    CatalogContextRecommendationService,
)
from soundmind.catalog_search import CatalogTextSearchService
from soundmind.config import AnalysisConfig
from soundmind.context_aware_flow import ContextAwareMusicFlow
from soundmind.embeddings.effnet import fetch_effnet_model
from soundmind.embeddings.learned_service import LearnedEmbeddingService
from soundmind.flow import EndToEndRequest
from soundmind.ingestion.scanner import scan_directory
from soundmind.recommendation.learned_retrieval import LearnedRetrievalEngine
from soundmind.recommendation.semantic_text_retrieval import (
    DEFAULT_TEXT_DOCUMENT_PREFIX,
    DEFAULT_TEXT_MODEL,
    DEFAULT_TEXT_QUERY_PREFIX,
    FastEmbedTextProvider,
)
from soundmind.sequence import SequenceMode
from soundmind.storage.database import create_session_factory


def _parse_now(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid ISO-8601 timestamp: {value!r}"
        ) from exc
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("timestamp must include a timezone")
    return parsed.astimezone(UTC)


def build_parser():
    p = argparse.ArgumentParser(prog="soundmind")
    s = p.add_subparsers(dest="command", required=True)

    scan = s.add_parser("scan")
    scan.add_argument("music_folder", type=Path)
    scan.add_argument("--db", type=Path, default=Path("data/database/soundmind.db"))
    scan.add_argument("--no-content-hash", action="store_true")
    scan.add_argument("--no-analysis", action="store_true")
    scan.add_argument("--analysis-seconds", type=float, default=180.0)
    scan.add_argument("--analysis-offset", type=float, default=0.0)

    m = s.add_parser("model")
    ms = m.add_subparsers(dest="model_command", required=True)
    f = ms.add_parser("fetch-effnet")
    f.add_argument(
        "--path",
        type=Path,
        default=Path("data/models/discogs-effnet-bsdynamic-1.onnx"),
    )

    li = s.add_parser("learned-index")
    ls = li.add_subparsers(dest="learned_command", required=True)
    r = ls.add_parser("rebuild")
    r.add_argument("--db", type=Path, default=Path("data/database/soundmind.db"))
    r.add_argument(
        "--model",
        type=Path,
        default=Path("data/models/discogs-effnet-bsdynamic-1.onnx"),
    )
    r.add_argument("--index", type=Path, default=Path("data/index/effnet_vectors"))
    r.add_argument("--limit", type=int)

    q = ls.add_parser("similar")
    q.add_argument("track_id")
    q.add_argument("--db", type=Path, default=Path("data/database/soundmind.db"))
    q.add_argument(
        "--model",
        type=Path,
        default=Path("data/models/discogs-effnet-bsdynamic-1.onnx"),
    )
    q.add_argument("--index", type=Path, default=Path("data/index/effnet_vectors"))
    q.add_argument("--limit", type=int, default=10)

    search = s.add_parser("search")
    search.add_argument("query")
    search.add_argument("--db", type=Path, default=Path("data/database/soundmind.db"))
    search.add_argument("--limit", type=int, default=10)
    search_mode = search.add_mutually_exclusive_group()
    search_mode.add_argument(
        "--semantic",
        action="store_true",
        help="use optional local text embeddings instead of lexical matching",
    )
    search_mode.add_argument(
        "--semantic-indexed",
        action="store_true",
        help="use a persisted local semantic index",
    )
    search.add_argument(
        "--hybrid",
        action="store_true",
        help=(
            "fuse lexical results with live semantic results, "
            "or with persisted-index results when --semantic-indexed is given"
        ),
    )
    search.add_argument(
        "--expand-query",
        action="store_true",
        help="expand supported music-domain phrases for lexical retrieval",
    )
    search.add_argument(
        "--explain-retrieval",
        action="store_true",
        help="print deterministic lexical or hybrid retrieval evidence",
    )
    search.add_argument("--semantic-model", default=DEFAULT_TEXT_MODEL)
    search.add_argument("--semantic-query-prefix", default=DEFAULT_TEXT_QUERY_PREFIX)
    search.add_argument("--semantic-document-prefix", default=DEFAULT_TEXT_DOCUMENT_PREFIX)
    search.add_argument(
        "--lexical-weight",
        type=float,
        default=0.5,
        help="hybrid fusion weight for lexical scores",
    )
    search.add_argument(
        "--semantic-weight",
        type=float,
        default=0.5,
        help="hybrid fusion weight for semantic scores",
    )
    search.add_argument(
        "--semantic-index",
        type=Path,
        default=Path("data/index/text_vectors"),
    )

    si = s.add_parser("semantic-index")
    sis = si.add_subparsers(dest="semantic_index_command", required=True)
    sir = sis.add_parser("rebuild")
    sir.add_argument("--db", type=Path, default=Path("data/database/soundmind.db"))
    sir.add_argument("--model", default=DEFAULT_TEXT_MODEL)
    sir.add_argument("--query-prefix", default=DEFAULT_TEXT_QUERY_PREFIX)
    sir.add_argument("--document-prefix", default=DEFAULT_TEXT_DOCUMENT_PREFIX)
    sir.add_argument(
        "--index",
        type=Path,
        default=Path("data/index/text_vectors"),
    )

    rec = s.add_parser("recommend")
    rec.add_argument("text")
    rec.add_argument("--context", required=True)
    rec.add_argument("--db", type=Path, default=Path("data/database/soundmind.db"))
    rec.add_argument("--limit", type=int, default=10)
    rec.add_argument("--catalog-limit", type=int)
    rec.add_argument("--event-limit", type=int, default=1000)
    rec.add_argument(
        "--expand-query",
        action="store_true",
        help="expand supported music-domain phrases for lexical retrieval",
    )
    rec.add_argument(
        "--lexical-weight",
        type=float,
        default=0.5,
        help="hybrid fusion weight for lexical scores",
    )
    rec.add_argument(
        "--semantic-weight",
        type=float,
        default=0.5,
        help="hybrid fusion weight for semantic scores",
    )
    rec.add_argument(
        "--retrieval",
        choices=RETRIEVAL_MODES,
        default="catalog",
        help=(
            "candidate generation mode: catalog, lexical, semantic, "
            "semantic-indexed, hybrid, or hybrid-indexed"
        ),
    )
    rec.add_argument(
        "--retrieval-limit",
        type=int,
        help="maximum candidates requested from the M12 retrieval layer",
    )
    rec.add_argument(
        "--text-model",
        default=DEFAULT_TEXT_MODEL,
        help="local text embedding model for semantic retrieval",
    )
    rec.add_argument("--text-query-prefix", default=DEFAULT_TEXT_QUERY_PREFIX)
    rec.add_argument("--text-document-prefix", default=DEFAULT_TEXT_DOCUMENT_PREFIX)
    rec.add_argument(
        "--text-index",
        type=Path,
        default=Path("data/index/text_vectors"),
        help="persisted text index for semantic-indexed and hybrid-indexed retrieval",
    )
    rec.add_argument(
        "--mode",
        choices=tuple(mode.value for mode in SequenceMode),
        default=SequenceMode.SMOOTH.value,
    )
    rec.add_argument("--now", type=_parse_now)
    rec.add_argument("--seed-track-id")
    rec.add_argument(
        "--model",
        type=Path,
        default=Path("data/models/discogs-effnet-bsdynamic-1.onnx"),
    )
    rec.add_argument(
        "--index",
        type=Path,
        default=Path("data/index/effnet_vectors"),
    )
    rec.add_argument(
        "--explain",
        action="store_true",
        help="print per-signal ranking contributions",
    )

    return p


def _print_search(results, *, explain=False) -> None:
    for index, result in enumerate(results, start=1):
        details = " — ".join(
            value for value in (result.title, result.artist, result.album) if value
        )
        matched = ", ".join(result.matched_fields)
        suffix = f"	{details}" if details else ""
        field_suffix = f"	matched={matched}" if matched else ""
        print(f"{index}. {result.track_id}	{result.score:.6f}{suffix}{field_suffix}")
        if explain and result.matched_query is not None:
            print(f"   matched-query: {result.matched_query}")


def _print_semantic_search(results) -> None:
    for index, result in enumerate(results, start=1):
        details = " — ".join(
            value for value in (result.title, result.artist, result.album) if value
        )
        suffix = f"	{details}" if details else ""
        print(f"{index}. {result.track_id}	{result.score:.6f}{suffix}	semantic")


def _print_hybrid_search(results, *, explain=False) -> None:
    for index, result in enumerate(results, start=1):
        details = " — ".join(
            value for value in (result.title, result.artist, result.album) if value
        )
        suffix = f"	{details}" if details else ""
        print(
            f"{index}. {result.track_id}	{result.score:.6f}{suffix}"
            f"	hybrid lexical={result.lexical_score:.6f}"
            f" semantic={result.semantic_score:.6f}"
        )
        if explain:
            print(f"   lexical-normalized-score: {result.lexical_normalized_score:.6f}")
            print(f"   semantic-normalized-score: {result.semantic_normalized_score:.6f}")
            print(f"   lexical-contribution: {result.lexical_contribution:.6f}")
            print(f"   semantic-contribution: {result.semantic_contribution:.6f}")


def _print_recommendation(result, *, explain=False) -> None:
    print(f"Intent: {result.intent.raw_text}")
    print("Ranked:")
    for index, candidate in enumerate(result.ranked, start=1):
        print(f"{index}. {candidate.track_id}	{candidate.score:.6f}")
        if explain:
            strongest = candidate.explanation.strongest_signal
            print(f"   strongest: {strongest or 'none'}")
            for contribution in candidate.explanation.contributions:
                print(
                    f"   {contribution.name}: "
                    f"raw={contribution.raw_score:.6f} "
                    f"weight={contribution.weight:.6f} "
                    f"contribution={contribution.contribution:.6f}"
                )
    print("Playlist:")
    for index, item in enumerate(result.playlist, start=1):
        print(f"{index}. {item.track_id}")


def _recommend_service(a, session):
    if a.seed_track_id is None:
        return CatalogContextRecommendationService(session)

    learned_service = LearnedEmbeddingService(
        session,
        model_path=a.model,
        index_path=a.index,
    )
    flow = ContextAwareMusicFlow(
        learned=LearnedRetrievalEngine(learned_service),
    )
    return CatalogContextRecommendationService(session, flow=flow)


def main(argv=None):
    a = build_parser().parse_args(argv)

    if a.command == "scan":
        sf = create_session_factory(a.db)
        with sf() as session:
            count = scan_directory(
                session,
                a.music_folder,
                compute_content_hash=not a.no_content_hash,
                analyze=not a.no_analysis,
                analysis_config=AnalysisConfig(
                    max_analysis_seconds=a.analysis_seconds,
                    analysis_offset_seconds=a.analysis_offset,
                ),
            )
        print(f"Scanned changed tracks: {count}")
        return 0

    if a.command == "model" and a.model_command == "fetch-effnet":
        print(fetch_effnet_model(a.path))
        return 0

    if a.command == "learned-index":
        sf = create_session_factory(a.db)
        with sf() as session:
            svc = LearnedEmbeddingService(
                session,
                model_path=a.model,
                index_path=a.index,
            )
            if a.learned_command == "rebuild":
                print(f"Indexed learned embeddings: {svc.rebuild(limit=a.limit)}")
                return 0
            for x in svc.similar(a.track_id, limit=a.limit):
                print(f"{x.track_id}	{x.score:.6f}")
            return 0

    if a.command == "search":
        sf = create_session_factory(a.db)
        with sf() as session:
            service = CatalogTextSearchService(session)
            if a.hybrid:
                provider = FastEmbedTextProvider(
                    a.semantic_model,
                    query_prefix=a.semantic_query_prefix,
                    document_prefix=a.semantic_document_prefix,
                )
                if a.semantic_indexed:
                    results = service.hybrid_search_indexed(
                        a.query,
                        provider=provider,
                        model_name=a.semantic_model,
                        index_path=a.semantic_index,
                        query_prefix=a.semantic_query_prefix,
                        document_prefix=a.semantic_document_prefix,
                        limit=a.limit,
                        lexical_weight=a.lexical_weight,
                        semantic_weight=a.semantic_weight,
                        expand=a.expand_query,
                    )
                else:
                    results = service.hybrid_search(
                        a.query,
                        provider=provider,
                        limit=a.limit,
                        lexical_weight=a.lexical_weight,
                        semantic_weight=a.semantic_weight,
                        expand=a.expand_query,
                    )
                _print_hybrid_search(results, explain=a.explain_retrieval)
            elif a.semantic:
                provider = FastEmbedTextProvider(
                    a.semantic_model,
                    query_prefix=a.semantic_query_prefix,
                    document_prefix=a.semantic_document_prefix,
                )
                results = service.semantic_search(
                    a.query,
                    provider=provider,
                    limit=a.limit,
                )
                _print_semantic_search(results)
            elif a.semantic_indexed:
                provider = FastEmbedTextProvider(
                    a.semantic_model,
                    query_prefix=a.semantic_query_prefix,
                    document_prefix=a.semantic_document_prefix,
                )
                results = service.semantic_search_indexed(
                    a.query,
                    provider=provider,
                    model_name=a.semantic_model,
                    index_path=a.semantic_index,
                    limit=a.limit,
                )
                for index, result in enumerate(results, start=1):
                    details = " — ".join(
                        value for value in (result.title, result.artist, result.album) if value
                    )
                    suffix = f"	{details}" if details else ""
                    print(f"{index}. {result.track_id}	{result.score:.6f}{suffix}	semantic-indexed")
            else:
                results = service.search(
                    a.query,
                    limit=a.limit,
                    expand=a.expand_query,
                )
                _print_search(results, explain=a.explain_retrieval)
        return 0

    if a.command == "semantic-index":
        sf = create_session_factory(a.db)
        with sf() as session:
            provider = FastEmbedTextProvider(
                a.model,
                query_prefix=a.query_prefix,
                document_prefix=a.document_prefix,
            )
            count = CatalogTextSearchService(session).rebuild_semantic_index(
                provider=provider,
                model_name=a.model,
                index_path=a.index,
                query_prefix=a.query_prefix,
                document_prefix=a.document_prefix,
            )
        print(f"Indexed semantic text vectors: {count}")
        return 0

    if a.command == "recommend":
        sf = create_session_factory(a.db)
        now = a.now or datetime.now(UTC)
        request = EndToEndRequest(
            text=a.text,
            candidates=(),
            mode=SequenceMode(a.mode),
            limit=a.limit,
        )
        with sf() as session:
            service = _recommend_service(a, session)
            recommend_kwargs = {
                "context": a.context,
                "now": now,
                "event_limit": a.event_limit,
                "catalog_limit": a.catalog_limit,
                "seed_track_id": a.seed_track_id,
            }
            if a.retrieval != "catalog":
                text_provider = (
                    FastEmbedTextProvider(
                        a.text_model,
                        query_prefix=a.text_query_prefix,
                        document_prefix=a.text_document_prefix,
                    )
                    if a.retrieval in {
                        "semantic",
                        "semantic-indexed",
                        "hybrid",
                        "hybrid-indexed",
                    }
                    else None
                )
                recommend_kwargs.update(
                    {
                        "retrieval_mode": a.retrieval,
                        "retrieval_limit": a.retrieval_limit,
                        "text_provider": text_provider,
                        "text_model": a.text_model,
                        "text_index_path": a.text_index,
                        "text_query_prefix": a.text_query_prefix,
                        "text_document_prefix": a.text_document_prefix,
                        "lexical_weight": a.lexical_weight,
                        "semantic_weight": a.semantic_weight,
                    }
                )
            result = service.recommend(request, **recommend_kwargs)
        _print_recommendation(result, explain=a.explain)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
