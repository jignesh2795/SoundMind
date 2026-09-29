from datetime import UTC, datetime, timedelta

import pytest

from soundmind.preferences.models import ListeningEvent, ListeningEventType
from soundmind.preferences.profile import TasteProfileBuilder


def test_like_is_positive():
    now=datetime.now(UTC); s=TasteProfileBuilder().signal(ListeningEvent("a",ListeningEventType.LIKE,now),now=now)
    assert s.positive==pytest.approx(1); assert s.net_preference==pytest.approx(1)

def test_skip_is_negative():
    now=datetime.now(UTC); s=TasteProfileBuilder().signal(ListeningEvent("a",ListeningEventType.SKIP,now),now=now)
    assert s.skip==pytest.approx(.75); assert s.net_preference==pytest.approx(-.75)

def test_old_event_decays():
    now=datetime.now(UTC); s=TasteProfileBuilder().signal(ListeningEvent("a",ListeningEventType.LIKE,now-timedelta(days=30)),now=now)
    assert s.positive==pytest.approx(.5)

def test_profile_context():
    now=datetime.now(UTC)
    p=TasteProfileBuilder().build([ListeningEvent("a",ListeningEventType.LIKE,now,context="night"),ListeningEvent("b",ListeningEventType.SKIP,now,context="coding")],now=now)
    assert p.positive_track_ids==("a",); assert p.negative_track_ids==(); assert p.skipped_track_ids==("b",); assert p.contexts==("coding","night")
