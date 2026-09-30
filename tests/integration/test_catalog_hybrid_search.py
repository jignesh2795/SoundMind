from datetime import UTC, datetime

import pytest

from soundmind.catalog_search import CatalogTextSearchService
from soundmind.recommendation.hybrid_retrieval import HybridWeights
from soundmind.storage.database import create_session_factory
from soundmind.storage.models import TrackRow


def row(track_id: str, *, title: str, artist: str, status: str = "active") -> TrackRow:
    now = datetime.now(UTC)
    return TrackRow(
        track_id=track_id,
        content_hash=track_id * 64,
        source_type="file",
        source_uri=f"file:///music/{track_id}.mp3",
        file_name=f"{track_id}.mp3",
        file_size=1,
        modified_at_ns=1,
        created_at=now,
        updated_at=now,
        status=status,
        title=title,
        artist=artist,
    )


class StaticProvider:
    def embed_query(self, text: str):
        return (1.0, 0.0)

    def embed_documents(self, texts):
        return tuple(
            (1.0, 0.0) if "hero" in text.casefold() else (0.0, 1.0) for text in texts
        )


def test_hybrid_search_fuses_lexical_and_live_semantic(tmp_path) -> None:
    factory = create_session_factory(tmp_path / "soundmind.db")
    with factory() as session:
        session.add_all(
            [
                row("lex", title="Mass Hero Entry", artist="Someone Else"),
                row("sem", title="Unrelated Words Here", artist="Another Name"),
            ]
        )
        session.commit()

        provider = StaticProvider()
        results = CatalogTextSearchService(session).hybrid_search(
            "hero entry",
            provider=provider,
            limit=10,
        )

    assert {result.track_id for result in results} == {"lex", "sem"}
    assert [result.track_id for result in results] == ["lex", "sem"]


def test_hybrid_search_supports_persisted_semantic_index(tmp_path) -> None:
    factory = create_session_factory(tmp_path / "soundmind.db")
    with factory() as session:
        session.add_all(
            [
                row("hero", title="Hero Entry", artist="Composer"),
                row("calm", title="Calm", artist="Composer"),
            ]
        )
        session.commit()

        service = CatalogTextSearchService(session)
        service.rebuild_semantic_index(
            provider=StaticProvider(),
            model_name="model-v1",
            index_path=tmp_path / "semantic_vectors",
        )
        results = service.hybrid_search_indexed(
            "hero",
            provider=StaticProvider(),
            model_name="model-v1",
            index_path=tmp_path / "semantic_vectors",
            limit=10,
        )

    assert [result.track_id for result in results] == ["hero", "calm"]
    assert results[0].lexical_score > 0


def test_hybrid_search_rejects_invalid_weights(tmp_path) -> None:
    factory = create_session_factory(tmp_path / "soundmind.db")
    with factory() as session:
        session.add(row("hero", title="Hero Entry", artist="Composer"))
        session.commit()

        with pytest.raises(ValueError):
            CatalogTextSearchService(session).hybrid_search(
                "hero",
                provider=StaticProvider(),
                lexical_weight=-1.0,
                semantic_weight=0.5,
            )


def test_hybrid_weights_must_be_positive() -> None:
    with pytest.raises(ValueError):
        HybridWeights(0.0, 0.0)
