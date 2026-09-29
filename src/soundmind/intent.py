"""M3 deterministic music-intent parser (see docs/m3-music-intent-contract.md)."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MusicIntent:
    raw_text: str
    genres: tuple[str, ...] = ()
    moods: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    regions: tuple[str, ...] = ()
    energy: float | None = None
    instrumentation: tuple[str, ...] = ()
    music_types: tuple[str, ...] = ()
    scenes: tuple[str, ...] = ()
    vocal_preference: str = "any"
    novelty: str = "any"
    negative_terms: tuple[str, ...] = ()
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if self.energy is not None and not 0.0 <= self.energy <= 1.0:
            raise ValueError("energy must be within 0..1")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within 0..1")
        if self.vocal_preference not in ("any", "instrumental", "vocal"):
            raise ValueError(f"invalid vocal_preference: {self.vocal_preference!r}")
        if self.novelty not in ("any", "familiar", "discovery"):
            raise ValueError(f"invalid novelty: {self.novelty!r}")


def _has(pattern: str, text: str) -> bool:
    return re.search(pattern, text) is not None


def parse_intent(text: str) -> MusicIntent:
    if text is None or not text.strip():
        raise ValueError("text must be non-empty")
    raw = text
    normalized = re.sub(r"[-_]+", " ", text.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()

    regions: set[str] = set()
    if _has(r"\bsouth\s+indians?\b", normalized) or _has(r"\bsouth\s+india\b", normalized):
        regions.add("south_india")

    languages: set[str] = set()
    for language in ("tamil", "telugu", "malayalam", "kannada"):
        if _has(rf"\b{language}\b", normalized):
            languages.add(language)

    music_types: set[str] = set()
    if _has(r"\bbgm\b", normalized) or _has(r"\bbackground\s+music\b", normalized):
        music_types.add("bgm")
    if _has(r"\bsoundtracks?\b", normalized):
        music_types.add("soundtrack")
    if _has(r"\bsongs?\b", normalized):
        music_types.add("song")

    scenes: set[str] = set()
    if _has(r"\bhero\s+entry\b", normalized) or _has(r"\bmass\s+entry\b", normalized):
        scenes.add("hero_entry")
    if _has(r"\bchase\b", normalized):
        scenes.add("chase")
    if _has(r"\bbattle\b", normalized) or _has(r"\bfight\b", normalized):
        scenes.add("battle")
    if _has(r"\bromance\b", normalized) or _has(r"\bromantic\b", normalized):
        scenes.add("romance")
    if _has(r"\bsuspense\b", normalized) or _has(r"\bthriller\b", normalized):
        scenes.add("suspense")
    if _has(r"\bclimax\b", normalized):
        scenes.add("climax")

    moods: set[str] = set()
    for mood in (
        "dark",
        "emotional",
        "sad",
        "happy",
        "cinematic",
        "mass",
        "folk",
        "classical",
        "electronic",
        "orchestral",
    ):
        if _has(rf"\b{mood}\b", normalized):
            moods.add(mood)

    energy: float | None = None
    if (
        _has(r"\bvery\s+high\b", normalized)
        or _has(r"\bvery\s+intense\b", normalized)
        or _has(r"\bintense\b", normalized)
    ):
        energy = 0.95
    elif _has(r"\bhigh\b", normalized) or _has(r"\benergetic\b", normalized):
        energy = 0.8
    elif _has(r"\bmedium\b", normalized) or _has(r"\bmoderate\b", normalized):
        energy = 0.5
    elif _has(r"\blow\b", normalized) or _has(r"\bcalm\b", normalized):
        energy = 0.3

    vocal_preference = "any"
    negative_terms: set[str] = set()
    if (
        _has(r"\bwithout\s+vocals?\b", normalized)
        or _has(r"\bno\s+vocals?\b", normalized)
        or _has(r"\bless\s+vocals?\b", normalized)
    ):
        vocal_preference = "instrumental"
        negative_terms.add("vocals")
    elif _has(r"\binstrumental\b", normalized):
        vocal_preference = "instrumental"
    elif _has(r"\bvocals?\b", normalized):
        vocal_preference = "vocal"

    novelty = "any"
    if (
        _has(r"\bsomething\s+new\b", normalized)
        or _has(r"\bdiscovery\b", normalized)
        or _has(r"\bdiscover\b", normalized)
    ):
        novelty = "discovery"
    elif (
        _has(r"\bsomething\s+i\s+know\b", normalized)
        or _has(r"\bfamiliar\b", normalized)
        or _has(r"\bknown\b", normalized)
    ):
        novelty = "familiar"

    hits = (
        len(regions)
        + len(languages)
        + len(music_types)
        + len(scenes)
        + len(moods)
        + (1 if energy is not None else 0)
        + (1 if vocal_preference != "any" else 0)
        + (1 if novelty != "any" else 0)
    )
    confidence = round(min(1.0, 0.2 * hits), 3)

    return MusicIntent(
        raw_text=raw,
        genres=(),
        moods=tuple(sorted(moods)),
        languages=tuple(sorted(languages)),
        regions=tuple(sorted(regions)),
        energy=energy,
        instrumentation=(),
        music_types=tuple(sorted(music_types)),
        scenes=tuple(sorted(scenes)),
        vocal_preference=vocal_preference,
        novelty=novelty,
        negative_terms=tuple(sorted(negative_terms)),
        confidence=confidence,
    )
