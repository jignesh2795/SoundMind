from datetime import datetime,timezone
from soundmind.preferences.models import ListeningEvent,ListeningEventType
from soundmind.preferences.repository import ListeningEventRepository
from soundmind.storage.database import create_session_factory

def test_round_trip(tmp_path):
    factory=create_session_factory(tmp_path/"soundmind.db"); now=datetime.now(timezone.utc)
    with factory() as session:
        repo=ListeningEventRepository(session); repo.add(ListeningEvent("track-1",ListeningEventType.LIKE,now,"night")); events=repo.list_recent()
    assert len(events)==1 and events[0].track_id=="track-1" and events[0].event_type is ListeningEventType.LIKE and events[0].context=="night"
