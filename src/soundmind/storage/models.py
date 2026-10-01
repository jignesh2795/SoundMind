from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from soundmind.storage.database import Base


class TrackRow(Base):
    __tablename__ = "tracks"
    track_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_uri: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    modified_at_ns: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    title: Mapped[str|None] = mapped_column(Text)
    artist: Mapped[str|None] = mapped_column(Text, index=True)
    album: Mapped[str|None] = mapped_column(Text, index=True)
    album_artist: Mapped[str|None] = mapped_column(Text)
    composer: Mapped[str|None] = mapped_column(Text, index=True)
    genre: Mapped[str|None] = mapped_column(Text)
    year: Mapped[int|None] = mapped_column(Integer)
    duration_seconds: Mapped[float|None] = mapped_column(Float)
    bitrate: Mapped[int|None] = mapped_column(Integer)
    sample_rate: Mapped[int|None] = mapped_column(Integer)
    channels: Mapped[int|None] = mapped_column(Integer)
    tempo_bpm: Mapped[float|None] = mapped_column(Float)
    rms_energy: Mapped[float|None] = mapped_column(Float)
    spectral_centroid: Mapped[float|None] = mapped_column(Float)
    spectral_bandwidth: Mapped[float|None] = mapped_column(Float)
    spectral_rolloff: Mapped[float|None] = mapped_column(Float)
    zero_crossing_rate: Mapped[float|None] = mapped_column(Float)
    mfcc_json: Mapped[str|None] = mapped_column(Text)
    chroma_json: Mapped[str|None] = mapped_column(Text)
    analysis_mode: Mapped[str|None] = mapped_column(String(32))
    analysis_seconds: Mapped[float|None] = mapped_column(Float)
    analysis_version: Mapped[str|None] = mapped_column(String(32))

class ScanStateRow(Base):
    __tablename__ = "scan_state"
    source_uri: Mapped[str] = mapped_column(Text, primary_key=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    modified_at_ns: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)



class PlaylistRow(Base):
    __tablename__ = "playlists"
    playlist_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PlaylistItemRow(Base):
    __tablename__ = "playlist_items"
    playlist_id: Mapped[int] = mapped_column(
        ForeignKey("playlists.playlist_id"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sequence_score: Mapped[float] = mapped_column(Float, nullable=False)
    base_score: Mapped[float] = mapped_column(Float, nullable=False)
