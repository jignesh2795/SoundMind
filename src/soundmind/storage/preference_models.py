from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from soundmind.storage.database import Base


class ListeningEventRow(Base):
    __tablename__="listening_events"
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    track_id:Mapped[str]=mapped_column(String(64),index=True,nullable=False)
    event_type:Mapped[str]=mapped_column(String(32),nullable=False,index=True)
    occurred_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,index=True)
    context:Mapped[str|None]=mapped_column(Text)
    seconds_played:Mapped[float|None]=mapped_column(Float)
