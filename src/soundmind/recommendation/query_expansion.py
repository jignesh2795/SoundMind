"""Deterministic, opt-in query expansion for music retrieval."""

from __future__ import annotations

import re

_QUERY_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("background score", ("background music", "bgm")),
    ("background music", ("bgm", "background score")),
    ("bgm", ("background music", "background score")),
    ("original soundtrack", ("ost", "soundtrack")),
    ("soundtrack", ("ost", "original soundtrack")),
    ("ost", ("soundtrack", "original soundtrack")),
    ("theme song", ("theme music",)),
    ("theme music", ("theme song",)),
    ("film score", ("movie score",)),
    ("movie score", ("film score",)),
)


def expand_query(query: str) -> tuple[str, ...]:
    """Return the original query plus deterministic music-domain variants."""
    if query is None or not query.strip():
        raise ValueError("query must be non-empty")

    normalized = " ".join(query.split())
    variants: list[str] = [normalized]
    lowered = normalized.casefold()

    for phrase, aliases in _QUERY_ALIASES:
        if re.search(rf"(?<!\\w){re.escape(phrase)}(?!\\w)", lowered):
            for alias in aliases:
                variants.append(
                    re.sub(
                        rf"(?<!\\w){re.escape(phrase)}(?!\\w)",
                        alias,
                        normalized,
                        flags=re.IGNORECASE,
                    )
                )

    return tuple(dict.fromkeys(variants))
