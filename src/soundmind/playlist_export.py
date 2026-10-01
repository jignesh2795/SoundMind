"""Deterministic JSON serialization for persisted playlist snapshots."""

from __future__ import annotations

import json

from soundmind.playlist_storage import SavedPlaylist


def saved_playlist_to_json(playlist: SavedPlaylist) -> str:
    """Serialize a saved playlist to a stable, human-readable JSON snapshot."""
    payload = {
        "version": 1,
        "name": playlist.name,
        "created_at": playlist.created_at.isoformat(),
        "updated_at": playlist.updated_at.isoformat(),
        "items": [
            {
                "position": position,
                "track_id": item.track_id,
                "sequence_score": item.sequence_score,
                "base_score": item.base_score,
            }
            for position, item in enumerate(playlist.items, start=1)
        ],
    }
    return json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
    ) + "\n"
