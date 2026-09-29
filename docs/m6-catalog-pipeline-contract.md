# M6 — Catalog-to-Pipeline Contract

## Goal

Connect the existing SQLite music catalog to the M5 orchestration flow without changing M3, M4, M1, or M2 contracts.

## Pipeline

```
SQLite tracks
    ↓
CatalogCandidateRepository
    ↓
EndToEndCandidate
    ↓
M5 EndToEndMusicFlow
    ↓
M3 → M4 → M1 → M2
    ↓
EndToEndResult
```

## Catalog evidence mapping

The adapter exposes only evidence already stored in `TrackRow`:

| TrackRow | M5 candidate |
| --- | --- |
| `track_id` | `track_id` |
| `genre` | `genres` |
| `rms_energy` | `energy` |
| `tempo_bpm` | `tempo_bpm` |
| title/artist/album | catalog display metadata |

RMS energy is bounded to the M2/M4 `0..1` energy contract.

The following remain unknown because the current catalog schema does not store them:

- language
- region
- mood
- instrumentation
- music type
- scene
- vocal type
- personal novelty
- learned preference
- diversity signal
- brightness

Unknown evidence is represented by the existing empty/neutral candidate fields rather than guessed values.

## Repository behavior

- Reads only rows with `status="active"`.
- Orders by stable `track_id`.
- Optional positive limit.
- Does not scan files.
- Does not run audio analysis.
- Does not mutate catalog rows.

## Architectural boundary

M6 deliberately keeps SQLite access outside M5. M5 continues to operate on structured candidates and can therefore later consume other sources without knowing where candidates came from.

Future milestones can enrich the catalog schema or add separate evidence providers for language, scene, cultural labels, learned preference, embeddings, and other Music DNA dimensions.
