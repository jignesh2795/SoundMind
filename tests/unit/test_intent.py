import pytest

from soundmind.intent import MusicIntent, parse_intent


def test_composes_south_indian_bgm_scene_and_mood():
    intent = parse_intent("dark South Indian movie BGM for a hero entry")
    assert intent.raw_text == "dark South Indian movie BGM for a hero entry"
    assert intent.regions == ("south_india",)
    assert intent.music_types == ("bgm",)
    assert intent.moods == ("dark",)
    assert intent.scenes == ("hero_entry",)
    assert intent.confidence > 0


def test_recognizes_language_and_scene_terms():
    intent = parse_intent("Tamil chase BGM")
    assert intent.languages == ("tamil",)
    assert intent.music_types == ("bgm",)
    assert intent.scenes == ("chase",)


@pytest.mark.parametrize(
    ("text", "energy"),
    [
        ("calm music", 0.3),
        ("medium energy", 0.5),
        ("high energy", 0.8),
        ("very intense music", 0.95),
    ],
)
def test_normalizes_energy_terms(text, energy):
    assert parse_intent(text).energy == energy


def test_recognizes_instrumental_and_discovery():
    intent = parse_intent("something new, instrumental, cinematic")
    assert intent.vocal_preference == "instrumental"
    assert intent.novelty == "discovery"
    assert intent.moods == ("cinematic",)


def test_unknown_text_is_not_fabricated_into_filters():
    intent = parse_intent("play something completely mysterious from another universe")
    assert intent.raw_text == "play something completely mysterious from another universe"
    assert intent.genres == ()
    assert intent.languages == ()
    assert intent.regions == ()
    assert intent.music_types == ()
    assert intent.scenes == ()
    assert intent.confidence == 0.0


def test_same_input_is_deterministic_and_collections_are_stable():
    text = "Tamil South Indian dark cinematic BGM chase electronic Tamil"
    first = parse_intent(text)
    second = parse_intent(text)
    assert first == second
    assert first.languages == ("tamil",)
    assert first.moods == ("cinematic", "dark", "electronic")


def test_empty_input_is_rejected():
    with pytest.raises(ValueError, match="text"):
        parse_intent("   ")


def test_intent_is_immutable():
    intent = parse_intent("dark BGM")
    assert isinstance(intent, MusicIntent)
    with pytest.raises(AttributeError):
        intent.raw_text = "changed"


def test_vocal_negation_is_supported():
    intent = parse_intent("South Indian BGM without vocals")
    assert intent.regions == ("south_india",)
    assert intent.music_types == ("bgm",)
    assert intent.vocal_preference == "instrumental"


def test_language_and_region_can_coexist():
    intent = parse_intent("Malayalam South Indian soundtrack")
    assert intent.languages == ("malayalam",)
    assert intent.regions == ("south_india",)
    assert intent.music_types == ("soundtrack",)
