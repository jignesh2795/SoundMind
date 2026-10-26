"""Offline, privacy-gated recommendation quality evaluation for M19."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import platform
import re
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from soundmind.catalog import CatalogCandidateRepository
from soundmind.catalog_search import CatalogTextSearchService
from soundmind.intent import parse_intent
from soundmind.recommendation.fusion import FusionWeights
from soundmind.recommendation.hybrid_retrieval import HybridWeights
from soundmind.recommendation.intent_retrieval import IntentRetrievalEngine
from soundmind.recommendation.semantic_text_retrieval import (
    DEFAULT_TEXT_DOCUMENT_PREFIX,
    DEFAULT_TEXT_MODEL,
    DEFAULT_TEXT_QUERY_PREFIX,
    FastEmbedTextProvider,
)
from soundmind.storage.models import TrackRow

DATASET_ID = "m19-queries"
SUPPORTED_MODES = ("catalog", "lexical", "semantic", "semantic-indexed", "hybrid", "hybrid-indexed")
METRICS = ("nDCG@10", "Recall@10", "MRR@10")
DEFAULT_DATASET = Path("datasets/m19/queries-v1.json")
DEFAULT_JUDGMENTS = Path("data/eval/judgments.local.json")
DEFAULT_REPORT = Path("data/eval/reports/baseline-report.json")
DEFAULT_DATABASE = Path("data/database/soundmind.db")
DEFAULT_TEXT_INDEX = Path("data/index/text_vectors")
_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")

REQUIRED_LIMITATIONS_BLOCK = """**Scale limits:**

- The query set is small (target 30). A single query can move a macro-average materially, so treat small deltas between runs as noise, not signal.
- No confidence interval is computed and no significance test is claimed at this size.
- Facet coverage is partial; uncovered facets are listed explicitly rather than assumed to generalize.

**Judge limits:**

- One judge, one listener. There is no inter-rater agreement to report and no cross-listener generalization.
- Grades reflect that listener's taste and reading of the query text.
- Grading is human and slow, so the judged fraction is partial by design.

**Pooling limits:**

- The pool is the union of top-10 results from the compared modes, so tracks no mode retrieved are unjudged by construction.
- Pooled recall is relative to the judged pool, not the corpus. It is not comparable to corpus-wide recall.
- A system outside the pool gets no credit for relevant-but-unjudged tracks.

**Metadata limits:**

- Judgments may lean on catalog metadata, which is itself incomplete; unknown attributes are recorded as unknown, not inferred.
- Whether optional semantic or hybrid modes were available when judgments were made is stated, since an unavailable mode narrows the pool."""


class EvaluationError(ValueError):
    """Invalid M19 input or evaluation configuration."""


class PrivacyGateError(EvaluationError):
    """Required local-only path cannot be proven ignored by Git."""


def gain(grade: int) -> int:
    if isinstance(grade, bool) or not isinstance(grade, int) or grade not in (0, 1, 2, 3):
        raise ValueError("grade must be an integer from 0 through 3")
    return 2**grade - 1


def dcg_at_10(result_ids: Sequence[str], grades: Mapping[str, int]) -> float:
    """Keep original ranks: an unjudged item contributes zero without being removed."""
    return math.fsum(
        gain(grades[track_id]) / math.log2(rank + 2) if track_id in grades else 0.0
        for rank, track_id in enumerate(result_ids[:10])
    )


def idcg_at_10(pool_ids: Sequence[str], grades: Mapping[str, int]) -> float:
    ideal = sorted(
        (grades[track_id] for track_id in pool_ids if track_id in grades),
        reverse=True,
    )[: min(10, len(pool_ids))]
    return math.fsum(gain(grade) / math.log2(rank + 2) for rank, grade in enumerate(ideal))


def recall_at_10(
    result_ids: Sequence[str], pool_ids: Sequence[str], grades: Mapping[str, int]
) -> float | None:
    relevant = {track_id for track_id in pool_ids if grades.get(track_id, -1) >= 2}
    if not relevant:
        return None
    return len({track_id for track_id in result_ids[:10] if track_id in relevant}) / len(relevant)


def mrr_at_10(result_ids: Sequence[str], grades: Mapping[str, int]) -> float:
    for rank, track_id in enumerate(result_ids[:10], start=1):
        if grades.get(track_id, -1) >= 2:
            return 1.0 / rank
    return 0.0


def build_frozen_pool(
    ordered_top10_by_mode: Mapping[str, Sequence[str]],
    candidate_limits: Mapping[str, int],
    *,
    dataset_version: str,
) -> dict[str, Any]:
    """Return a deterministic pool manifest for one query, preserving each mode's ranks."""
    if not isinstance(ordered_top10_by_mode, Mapping) or not ordered_top10_by_mode:
        raise EvaluationError("at least one compared retrieval mode is required")
    modes = sorted(ordered_top10_by_mode)
    if set(candidate_limits) != set(modes):
        raise EvaluationError("candidate_limits must match the compared modes")
    members: list[str] = []
    seen: set[str] = set()
    ordered: dict[str, list[str]] = {}
    limits: dict[str, int] = {}
    for mode in modes:
        rows = ordered_top10_by_mode[mode]
        if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence) or len(rows) > 10:
            raise EvaluationError(f"{mode} results must be a sequence of at most 10 track IDs")
        ids = list(rows)
        if any(not isinstance(track_id, str) or not track_id.strip() for track_id in ids):
            raise EvaluationError(f"{mode} results contain an invalid track ID")
        if len(ids) != len(set(ids)):
            raise EvaluationError(f"{mode} results contain duplicate track IDs")
        limit = candidate_limits[mode]
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise EvaluationError(f"candidate limit for {mode} must be a positive integer")
        ordered[mode] = ids
        limits[mode] = limit
        for track_id in ids:
            if track_id not in seen:
                seen.add(track_id)
                members.append(track_id)
    return {
        "dataset_version": dataset_version,
        "modes_compared": modes,
        "candidate_limits": limits,
        "ordered_top10_by_mode": ordered,
        "members": members,
    }


def check_evaluability(
    frozen_pool: Sequence[str],
    grades_by_track: Mapping[str, int],
    returned_ids: Sequence[str],
    *,
    minimum_judged: int = 3,
) -> tuple[bool, list[str]]:
    """Check one query's judgments; never use grades from another query."""
    pool = set(frozen_pool)
    reasons: list[str] = []
    if set(returned_ids) - pool:
        reasons.append("pool: returned tracks outside frozen pool")
    unjudged = pool - set(grades_by_track)
    if unjudged:
        reasons.append(f"pool incomplete: {len(unjudged)} of {len(pool)} pooled tracks unjudged")
    judged_count = len(pool.intersection(grades_by_track))
    if judged_count < minimum_judged:
        reasons.append(f"pool too small: {judged_count} judged tracks; minimum is {minimum_judged}")
    relevant_count = sum(grades_by_track.get(track_id, -1) >= 2 for track_id in pool)
    if relevant_count == 0:
        reasons.append("no judged-relevant tracks in frozen pool")
    if idcg_at_10(tuple(frozen_pool), grades_by_track) == 0.0:
        reasons.append("IDCG@10 = 0: all judged grades are 0")
    return not reasons, reasons


def evaluate_query(
    frozen_pool: Sequence[str],
    grades_by_track: Mapping[str, int],
    returned_ids: Sequence[str],
) -> dict[str, Any]:
    if len(returned_ids) != len(set(returned_ids)):
        return {
            "status": "not_evaluable",
            "reasons": ["retrieval returned duplicate track IDs"],
            "metrics": dict.fromkeys(METRICS),
        }
    evaluable, reasons = check_evaluability(frozen_pool, grades_by_track, returned_ids)
    if not evaluable:
        return {"status": "not_evaluable", "reasons": reasons, "metrics": dict.fromkeys(METRICS)}
    dcg = dcg_at_10(returned_ids, grades_by_track)
    idcg = idcg_at_10(frozen_pool, grades_by_track)
    recall = recall_at_10(returned_ids, frozen_pool, grades_by_track)
    if idcg <= 0 or recall is None:
        return {
            "status": "not_evaluable",
            "reasons": ["metric precondition failed after evaluability gate"],
            "metrics": dict.fromkeys(METRICS),
        }
    return {
        "status": "evaluable",
        "reasons": [],
        "metrics": {
            "nDCG@10": dcg / idcg,
            "Recall@10": recall,
            "MRR@10": mrr_at_10(returned_ids, grades_by_track),
        },
    }


def _read_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        doc = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluationError(f"cannot read valid {label} JSON") from exc
    if not isinstance(doc, dict):
        raise EvaluationError(f"{label} must be a JSON object")
    return doc, raw


def validate_queries(doc: Mapping[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    if doc.get("dataset") != DATASET_ID:
        raise EvaluationError(f"dataset must be {DATASET_ID!r}")
    version = doc.get("version")
    if not isinstance(version, str) or not _VERSION.fullmatch(version):
        raise EvaluationError("dataset version must use MAJOR.MINOR.PATCH")
    queries = doc.get("queries")
    if not isinstance(queries, list) or not queries:
        raise EvaluationError("queries must be a non-empty array")
    seen: set[str] = set()
    for position, query in enumerate(queries, start=1):
        if not isinstance(query, dict):
            raise EvaluationError(f"query {position} must be an object")
        query_id, text = query.get("id"), query.get("text")
        if not isinstance(query_id, str) or not query_id.strip() or query_id in seen:
            raise EvaluationError(f"query {position} has a missing or duplicate id")
        if not isinstance(text, str) or not text.strip():
            raise EvaluationError(f"query {query_id} has empty text")
        if not isinstance(query.get("facets", {}), dict):
            raise EvaluationError(f"query {query_id} facets must be an object")
        seen.add(query_id)
    return version, queries


def validate_judgments(
    doc: Mapping[str, Any], *, version: str, query_ids: set[str]
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, int]]]:
    if doc.get("dataset") != DATASET_ID or doc.get("dataset_version") != version:
        raise EvaluationError("judgment dataset and dataset version must match the query dataset")
    if not isinstance(doc.get("catalog_fingerprint"), str) or not doc["catalog_fingerprint"].strip():
        raise EvaluationError("catalog_fingerprint must be a non-empty string")
    stamp = doc.get("judged_at")
    try:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00")) if isinstance(stamp, str) else None
    except ValueError as exc:
        raise EvaluationError("judged_at must be timezone-aware ISO-8601") from exc
    if parsed is None or parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EvaluationError("judged_at must be timezone-aware ISO-8601")

    manifest = doc.get("pool_manifest")
    if not isinstance(manifest, dict) or manifest.get("dataset_version") != version:
        raise EvaluationError("a frozen pool manifest matching the dataset version is required")
    pools = manifest.get("queries")
    if not isinstance(pools, dict) or set(pools) != query_ids:
        raise EvaluationError("pool manifest must contain exactly one entry per query")

    clean_pools: dict[str, dict[str, Any]] = {}
    for query_id, entry in pools.items():
        if not isinstance(entry, dict) or entry.get("dataset_version") != version:
            raise EvaluationError(f"invalid pool manifest for {query_id}")
        members, modes = entry.get("members"), entry.get("modes_compared")
        limits, ordered = entry.get("candidate_limits"), entry.get("ordered_top10_by_mode")
        if not isinstance(members, list) or any(not isinstance(x, str) or not x.strip() for x in members):
            raise EvaluationError(f"invalid pool members for {query_id}")
        if len(members) != len(set(members)):
            raise EvaluationError(f"duplicate pool members for {query_id}")
        if (not isinstance(modes, list) or not modes
                or any(not isinstance(mode, str) or mode not in SUPPORTED_MODES for mode in modes)
                or len(modes) != len(set(modes))):
            raise EvaluationError(f"invalid modes_compared for {query_id}")
        if not isinstance(limits, dict) or set(limits) != set(modes):
            raise EvaluationError(f"candidate_limits must match modes_compared for {query_id}")
        if not isinstance(ordered, dict) or set(ordered) != set(modes):
            raise EvaluationError(f"ordered results must match modes_compared for {query_id}")
        union: set[str] = set()
        clean_order: dict[str, list[str]] = {}
        for mode in modes:
            limit, results = limits[mode], ordered[mode]
            if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
                raise EvaluationError(f"invalid candidate limit for {mode}")
            if not isinstance(results, list) or len(results) > 10:
                raise EvaluationError(f"ordered results for {mode} must contain at most 10 IDs")
            if any(not isinstance(x, str) or not x.strip() for x in results):
                raise EvaluationError(f"invalid result ID in {mode} provenance")
            if len(results) != len(set(results)):
                raise EvaluationError(f"duplicate result ID in {mode} provenance")
            clean_order[mode] = list(results)
            union.update(results)
        if union != set(members):
            raise EvaluationError(f"pool members disagree with ordered provenance for {query_id}")
        clean_pools[query_id] = {
            **entry,
            "members": list(members),
            "modes_compared": list(modes),
            "candidate_limits": dict(limits),
            "ordered_top10_by_mode": clean_order,
        }

    raw = doc.get("judgments")
    if not isinstance(raw, list):
        raise EvaluationError("judgments must be an array")
    grades: dict[str, dict[str, int]] = {query_id: {} for query_id in query_ids}
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise EvaluationError(f"judgment {index} must be an object")
        query_id, track_id, grade = item.get("query_id"), item.get("track_id"), item.get("grade")
        if query_id not in query_ids:
            raise EvaluationError(f"judgment {index} references an unknown query")
        if not isinstance(track_id, str) or not track_id.strip():
            raise EvaluationError(f"judgment {index} has an invalid track ID")
        if isinstance(grade, bool) or not isinstance(grade, int) or grade not in (0, 1, 2, 3):
            raise EvaluationError(f"judgment {index} grade must be an integer from 0 through 3")
        if track_id not in clean_pools[query_id]["members"]:
            raise EvaluationError(f"judgment for {query_id} references a track outside its frozen pool")
        if track_id in grades[query_id]:
            raise EvaluationError(f"duplicate judgment for {query_id}/{track_id}")
        grades[query_id][track_id] = grade
    return clean_pools, grades


def _repo_root(start: Path) -> Path:
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise PrivacyGateError("Git is unavailable; refusing evaluation I/O") from exc
    if result.returncode != 0 or not result.stdout.strip():
        raise PrivacyGateError("cannot determine Git repository root; refusing evaluation I/O")
    return Path(result.stdout.strip()).resolve()


def _resolve_eval_path(root: Path, path: Path, label: str) -> Path:
    eval_root = (root / "data" / "eval").resolve()
    try:
        eval_root.relative_to(root.resolve())
    except ValueError as exc:
        raise PrivacyGateError("data/eval resolves outside the repository") from exc
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        resolved.relative_to(eval_root)
    except ValueError as exc:
        raise PrivacyGateError(f"{label} must remain inside data/eval") from exc
    return resolved


def _require_ignored(root: Path, path: Path, label: str) -> None:
    relative = path.relative_to(root).as_posix()
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-v", "--", relative],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise PrivacyGateError("Git ignore verification failed; refusing evaluation I/O") from exc
    if result.returncode != 0 or not result.stdout.strip():
        raise PrivacyGateError(f"{label} is not verifiably ignored; refusing evaluation I/O")


def enforce_privacy_gate(
    *,
    repo_root: Path | None = None,
    judgments_path: Path = DEFAULT_JUDGMENTS,
    output_path: Path = DEFAULT_REPORT,
) -> tuple[Path, Path, Path]:
    """Verify canonical and supplied paths before any output directory or file is created."""
    root = _repo_root(repo_root or Path.cwd())
    canonical_judgments = _resolve_eval_path(root, DEFAULT_JUDGMENTS, "canonical judgments")
    canonical_report = _resolve_eval_path(root, DEFAULT_REPORT, "canonical report")
    local_judgments = _resolve_eval_path(root, judgments_path, "judgments path")
    local_output = _resolve_eval_path(root, output_path, "report output path")
    if local_judgments == local_output:
        raise PrivacyGateError("judgments and report paths must be different")
    for path, label in (
        (canonical_judgments, "canonical judgment path"),
        (canonical_report, "canonical report path"),
        (local_judgments, "selected judgment path"),
        (local_output, "selected report path"),
    ):
        _require_ignored(root, path, label)
    return root, local_judgments, local_output


def _cached_model_reason(root: Path) -> str | None:
    if importlib.util.find_spec("fastembed") is None:
        return "optional dependency fastembed is not installed"
    slug = DEFAULT_TEXT_MODEL.rsplit("/", 1)[-1].casefold()
    roots = [
        root / "data" / "models",
        Path.home() / ".cache" / "fastembed",
        Path.home() / ".cache" / "huggingface" / "hub",
    ]
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        local = Path(local_app_data)
        roots.extend([local / "fastembed", local / "Temp" / "fastembed_cache"])
    for base in roots:
        if not base.is_dir():
            continue
        try:
            for item in [base, *base.iterdir()]:
                if slug in item.as_posix().casefold():
                    if item.is_file() and item.suffix.casefold() == ".onnx":
                        return None
                    if item.is_dir() and any(item.rglob("*.onnx")):
                        return None
        except OSError:
            continue
    return "local text model is not cached; M19 will not download model assets"


def mode_availability(root: Path) -> dict[str, dict[str, str]]:
    availability = {
        "catalog": {"status": "available", "reason": ""},
        "lexical": {"status": "available", "reason": ""},
    }
    model_reason = _cached_model_reason(root)
    index_path = root / DEFAULT_TEXT_INDEX
    index_ready = index_path.is_dir() and any(index_path.iterdir())
    for mode in ("semantic", "semantic-indexed", "hybrid", "hybrid-indexed"):
        reason = model_reason or (
            "local semantic index is missing or empty"
            if mode in ("semantic-indexed", "hybrid-indexed") and not index_ready
            else ""
        )
        availability[mode] = {"status": "unavailable" if reason else "available", "reason": reason}
    return availability


def _retrieve(session: Any, query: str, mode: str, limit: int, root: Path) -> list[str]:
    if mode == "catalog":
        candidates = CatalogCandidateRepository(session).candidates()
        ranked = IntentRetrievalEngine().rank(
            parse_intent(query), (row.candidate.intent_candidate for row in candidates), limit=limit
        )
        return [item.track_id for item in ranked]
    search = CatalogTextSearchService(session)
    if mode == "lexical":
        return [item.track_id for item in search.search(query, limit=limit)]
    reason = _cached_model_reason(root)
    if reason:
        raise RuntimeError(reason)
    provider = FastEmbedTextProvider(
        DEFAULT_TEXT_MODEL,
        query_prefix=DEFAULT_TEXT_QUERY_PREFIX,
        document_prefix=DEFAULT_TEXT_DOCUMENT_PREFIX,
    )
    if mode == "semantic":
        results = search.semantic_search(query, provider=provider, limit=limit)
    elif mode == "semantic-indexed":
        results = search.semantic_search_indexed(
            query, provider=provider, model_name=DEFAULT_TEXT_MODEL,
            index_path=root / DEFAULT_TEXT_INDEX, limit=limit,
        )
    elif mode == "hybrid":
        results = search.hybrid_search(query, provider=provider, limit=limit)
    elif mode == "hybrid-indexed":
        results = search.hybrid_search_indexed(
            query, provider=provider, model_name=DEFAULT_TEXT_MODEL,
            index_path=root / DEFAULT_TEXT_INDEX, limit=limit,
        )
    else:
        raise EvaluationError(f"unsupported retrieval mode: {mode}")
    return [item.track_id for item in results]


def _evidence_coverage(
    query: Mapping[str, Any],
    result_ids: Sequence[str],
    rows: Mapping[str, TrackRow],
    catalog_size: int,
) -> dict[str, Any]:
    candidate_coverage = len(result_ids) / catalog_size if catalog_size else None
    facets = {
        key: value for key, value in query.get("facets", {}).items()
        if value not in (None, "", [], {})
    }
    if not facets or not result_ids:
        return {
            "candidate_pool_coverage": candidate_coverage,
            "missing_evidence_rate": None,
            "missing_evidence_count": 0,
            "evidence_opportunities": 0,
        }
    fields = {
        "genre": "genre", "energy": "rms_energy", "tempo": "tempo_bpm",
        "artist": "artist", "album": "album", "year": "year",
    }
    missing = 0
    opportunities = 0
    for track_id in result_ids:
        for facet in facets:
            opportunities += 1
            field = fields.get(facet)
            value = getattr(rows.get(track_id), field, None) if field else None
            if value is None or value == "":
                missing += 1
    return {
        "candidate_pool_coverage": candidate_coverage,
        "missing_evidence_rate": missing / opportunities if opportunities else None,
        "missing_evidence_count": missing,
        "evidence_opportunities": opportunities,
    }


def _summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for metric in METRICS:
        values = [
            item["metrics"][metric] for item in results
            if item["status"] == "evaluable" and item["metrics"][metric] is not None
        ]
        failures = Counter(
            reason for item in results if item["status"] != "evaluable"
            for reason in item["reasons"]
        )
        summary[metric] = {
            "value": round(math.fsum(values) / len(values), 8) if values else None,
            "evaluable_queries": len(values),
            "total_queries": len(results),
            "failure_counts_by_reason": dict(sorted(failures.items())),
            "null_reason": None if values else "no evaluable queries",
        }
    return summary


def _write_report(path: Path, report: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as stream:
            temp_name = stream.name
            json.dump(report, stream, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
        Path(temp_name).replace(path)
    finally:
        if temp_name:
            Path(temp_name).unlink(missing_ok=True)


def _readonly_sessions(database_path: Path):
    if not database_path.is_file():
        raise EvaluationError("configured SQLite catalog does not exist")
    uri = f"{database_path.resolve().as_uri()}?mode=ro&uri=true"
    engine = create_engine(f"sqlite+pysqlite:///{uri}", connect_args={"uri": True}, future=True)
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA query_only=ON")
        connection.execute(select(1))
    return sessionmaker(engine, expire_on_commit=False), engine


def run_evaluation(
    *,
    dataset_path: Path = DEFAULT_DATASET,
    judgments_path: Path = DEFAULT_JUDGMENTS,
    retrieval: str = "catalog",
    limit: int = 10,
    output_path: Path = DEFAULT_REPORT,
    database_path: Path = DEFAULT_DATABASE,
    repo_root: Path | None = None,
) -> int:
    """Run a local evaluation. Privacy checks precede output I/O; SQLite is read-only."""
    try:
        if retrieval not in SUPPORTED_MODES:
            raise EvaluationError(f"unsupported retrieval mode: {retrieval}")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise EvaluationError("limit must be a positive integer")
        root, judgments_file, report_file = enforce_privacy_gate(
            repo_root=repo_root,
            judgments_path=judgments_path,
            output_path=output_path,
        )
        query_doc, query_bytes = _read_json(dataset_path, "query dataset")
        version, queries = validate_queries(query_doc)
        judgment_doc, judgment_bytes = _read_json(judgments_file, "judgments")
        pools, grades_by_query = validate_judgments(
            judgment_doc, version=version, query_ids={query["id"] for query in queries}
        )

        availability = mode_availability(root)
        reason = (
            availability[retrieval]["reason"]
            if availability[retrieval]["status"] == "unavailable" else ""
        )
        active_size = 0
        rows_by_id: dict[str, TrackRow] = {}
        outputs: dict[str, list[str]] = {}
        engine = None
        if not reason:
            try:
                db_path = database_path if database_path.is_absolute() else root / database_path
                sessions, engine = _readonly_sessions(db_path)
                with sessions() as session:
                    rows = list(session.scalars(
                        select(TrackRow).where(TrackRow.status == "active").order_by(TrackRow.track_id)
                    ))
                    active_size = len(rows)
                    rows_by_id = {row.track_id: row for row in rows}
                    for query in queries:
                        outputs[query["id"]] = _retrieve(
                            session, query["text"], retrieval, limit, root
                        )
            except (EvaluationError, RuntimeError, SQLAlchemyError, OSError, ValueError) as exc:
                reason = str(exc) or "retrieval mode failed"
                availability[retrieval] = {"status": "unavailable", "reason": reason}
                outputs.clear()
            finally:
                if engine is not None:
                    engine.dispose()

        details: list[dict[str, Any]] = []
        total_pool = 0
        total_judged = 0
        coverage_values: list[float] = []
        evidence_missing = 0
        evidence_opportunities = 0
        for query in queries:
            query_id = query["id"]
            pool = pools[query_id]["members"]
            grades = grades_by_query[query_id]
            judged_count = len(set(pool).intersection(grades))
            total_pool += len(pool)
            total_judged += judged_count
            returned = outputs.get(query_id, []) if not reason else []
            if reason:
                evaluated = {
                    "status": "unavailable",
                    "reasons": [f"retrieval unavailable: {reason}"],
                    "metrics": dict.fromkeys(METRICS),
                }
                evidence = {
                    "candidate_pool_coverage": None,
                    "missing_evidence_rate": None,
                    "missing_evidence_count": 0,
                    "evidence_opportunities": 0,
                }
            else:
                evaluated = evaluate_query(pool, grades, returned)
                evidence = _evidence_coverage(query, returned, rows_by_id, active_size)
                if evidence["candidate_pool_coverage"] is not None:
                    coverage_values.append(evidence["candidate_pool_coverage"])
                evidence_missing += evidence["missing_evidence_count"]
                evidence_opportunities += evidence["evidence_opportunities"]
            details.append({
                "query_id": query_id,
                **evaluated,
                "returned_track_ids": returned,
                "frozen_pool_size": len(pool),
                "judged_pool_tracks": judged_count,
                "unjudged_pool_tracks": len(set(pool) - set(grades)),
                "pool_coverage": judged_count / len(pool) if pool else None,
                **evidence,
            })

        config: dict[str, Any] = {
            "retrieval": retrieval, "candidate_limit": limit, "query_expansion": False
        }
        if retrieval == "catalog":
            weights = FusionWeights().normalized()
            config["ranking_fusion_weights"] = {
                "metadata": weights.metadata, "dsp": weights.dsp, "learned": weights.learned,
                "preference": weights.preference, "novelty": weights.novelty,
                "diversity": weights.diversity,
            }
        elif retrieval in ("hybrid", "hybrid-indexed"):
            weights = HybridWeights().normalized()
            config["retrieval_fusion_weights"] = {
                "lexical": weights.lexical, "semantic": weights.semantic
            }
        if retrieval in ("semantic", "semantic-indexed", "hybrid", "hybrid-indexed"):
            config["model"] = DEFAULT_TEXT_MODEL
        if retrieval in ("semantic-indexed", "hybrid-indexed"):
            config["index_path"] = DEFAULT_TEXT_INDEX.as_posix()

        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip()
        report = {
            "report_schema_version": 1,
            "dataset": query_doc["dataset"],
            "dataset_version": version,
            "query_dataset_sha256": hashlib.sha256(query_bytes).hexdigest(),
            "judgments_sha256": hashlib.sha256(judgment_bytes).hexdigest(),
            "catalog_fingerprint": judgment_doc["catalog_fingerprint"],
            "code_revision": revision,
            "retrieval_configuration": config,
            "mode_availability": availability,
            "selected_mode_status": "unavailable" if reason else "available",
            "selected_mode_reason": reason or None,
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "python_version": platform.python_version(),
            "platform": platform.system(),
            "summary": _summarize(details),
            "coverage": {
                "pool_coverage": total_judged / total_pool if total_pool else None,
                "judged_pool_tracks": total_judged,
                "frozen_pool_tracks": total_pool,
                "candidate_pool_coverage": round(
                    math.fsum(coverage_values) / len(coverage_values), 8
                ) if coverage_values else None,
                "missing_evidence_rate": evidence_missing / evidence_opportunities
                if evidence_opportunities else None,
                "missing_evidence_count": evidence_missing,
                "evidence_opportunities": evidence_opportunities,
                "evaluable_queries": sum(item["status"] == "evaluable" for item in details),
                "total_queries": len(details),
                "gate_failure_counts_by_reason": dict(sorted(Counter(
                    reason_text for item in details if item["status"] != "evaluable"
                    for reason_text in item["reasons"]
                ).items())),
            },
            "queries": details,
            "limitations": REQUIRED_LIMITATIONS_BLOCK,
        }
        _write_report(report_file, report)
        print(f"M19 report written: {report_file.relative_to(root).as_posix()}")
        if reason:
            print(f"Selected retrieval mode unavailable: {reason}", file=sys.stderr)
        return 0
    except PrivacyGateError as exc:
        print(f"M19 privacy gate blocked evaluation: {exc}", file=sys.stderr)
        return 2
    except (EvaluationError, OSError, SQLAlchemyError, TypeError, ValueError,
            subprocess.SubprocessError) as exc:
        print(f"M19 evaluation failed: {exc}", file=sys.stderr)
        return 1


def compare_reports(
    *,
    baseline_path: Path,
    candidate_path: Path,
    repo_root: Path | None = None,
) -> int:
    """Print metric deltas for two local reports without writing files."""
    try:
        root, baseline_file, candidate_file = enforce_privacy_gate(
            repo_root=repo_root,
            judgments_path=baseline_path,
            output_path=candidate_path,
        )
        baseline, _ = _read_json(baseline_file, "baseline report")
        candidate, _ = _read_json(candidate_file, "candidate report")
        if baseline.get("dataset") != candidate.get("dataset"):
            raise EvaluationError("baseline and candidate datasets do not match")
        if baseline.get("dataset_version") != candidate.get("dataset_version"):
            raise EvaluationError("cannot compare different dataset versions")
        metrics: dict[str, Any] = {}
        for metric in METRICS:
            left = baseline.get("summary", {}).get(metric, {}).get("value")
            right = candidate.get("summary", {}).get(metric, {}).get("value")
            metrics[metric] = {
                "baseline": left,
                "candidate": right,
                "delta": round(right - left, 8) if left is not None and right is not None else None,
                "reason": None if left is not None and right is not None
                else "one or both reports have no evaluable queries",
            }
        print(json.dumps({
            "dataset": baseline["dataset"],
            "dataset_version": baseline["dataset_version"],
            "baseline_revision": baseline.get("code_revision"),
            "candidate_revision": candidate.get("code_revision"),
            "metrics": metrics,
        }, indent=2, sort_keys=True))
        return 0
    except PrivacyGateError as exc:
        print(f"M19 privacy gate blocked comparison: {exc}", file=sys.stderr)
        return 2
    except (EvaluationError, OSError, TypeError) as exc:
        print(f"M19 comparison failed: {exc}", file=sys.stderr)
        return 1
