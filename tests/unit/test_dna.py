from soundmind.dna import MusicDNA, normalized_brightness


def test_normalized_brightness_uses_nyquist_frequency() -> None:
    assert normalized_brightness(4000.0, 16000) == 0.5


def test_normalized_brightness_is_bounded() -> None:
    assert normalized_brightness(-100.0, 16000) == 0.0
    assert normalized_brightness(12000.0, 16000) == 1.0


def test_normalized_brightness_is_unknown_without_required_evidence() -> None:
    assert normalized_brightness(None, 16000) is None
    assert normalized_brightness(4000.0, None) is None
    assert normalized_brightness(4000.0, 0) is None


def test_music_dna_is_immutable_structured_evidence() -> None:
    dna = MusicDNA(
        tempo_bpm=120.0,
        energy=0.6,
        brightness=0.5,
        mfcc=(1.0, 2.0),
        chroma=(0.1, 0.2),
    )

    assert dna.tempo_bpm == 120.0
    assert dna.energy == 0.6
    assert dna.brightness == 0.5
    assert dna.mfcc == (1.0, 2.0)
    assert dna.chroma == (0.1, 0.2)