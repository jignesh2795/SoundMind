from datetime import UTC, datetime

from sqlalchemy import select

from soundmind.preferences.models import ListeningEvent, ListeningEventType
from soundmind.storage.preference_models import ListeningEventRow


class ListeningEventRepository:
    def __init__(self, session):
        self.session = session

    def add(self, event):
        row = ListeningEventRow(
            track_id=event.track_id,
            event_type=event.event_type.value,
            occurred_at=event.occurred_at,
            context=event.context,
            seconds_played=event.seconds_played,
        )
        self.session.add(row)
        self.session.commit()
        return row

    def list_recent(self, *, limit=1000):
        if limit <= 0:
            raise ValueError("limit must be positive")
        rows = self.session.scalars(
            select(ListeningEventRow)
            .order_by(ListeningEventRow.occurred_at.desc())
            .limit(limit)
        ).all()
        return [
            ListeningEvent(
                r.track_id,
                ListeningEventType(r.event_type),
                self._as_utc(r.occurred_at),
                r.context,
                r.seconds_played,
            )
            for r in rows
        ]

    def add_now(self, track_id, event_type, *, context=None, seconds_played=None):
        return self.add(
            ListeningEvent(
                track_id,
                event_type,
                datetime.now(UTC),
                context,
                seconds_played,
            )
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
