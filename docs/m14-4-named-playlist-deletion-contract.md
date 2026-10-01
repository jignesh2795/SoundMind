# M14.4 — Named Playlist Deletion

## Purpose

M14.4 completes the basic named-playlist lifecycle with explicit deletion of an existing persisted playlist snapshot.

## Command

`playlist delete NAME` resolves the named playlist using the M14.1 normalization rules, removes its persisted item rows and playlist row through `PlaylistRepository`, commits the transaction, and prints a deterministic confirmation.

Name lookup is case-insensitive and whitespace-normalized.

A missing playlist raises the existing explicit `ValueError` used by `playlist show` and `playlist edit`.

## Persistence semantics

`PlaylistRepository.delete(name)` is a transaction-participating repository primitive and does not commit by itself.

Deletion removes the associated `playlist_items` rows before deleting the parent `playlists` row. The caller owns the final transaction commit.

A successful CLI deletion commits once. A missing playlist does not invoke repository deletion or commit.

## Boundaries

M14.4 does not:

- regenerate or modify recommendations;
- invoke M1 ranking;
- invoke M2 sequencing;
- run playlist editing;
- alter catalog tracks or listening history;
- add playback or external synchronization;
- require an LLM, network service, or cloud model.

## Output

```text
soundmind playlist delete "Focus Music"

Deleted playlist: Focus Music
```

## Validation

M14.4 requires the normal project gate before closeout:

```text
Ruff: All checks passed!
pytest: <validated count> passed, 0 failed
git diff --check: clean
working tree: clean
```

Validated gate at merged implementation head `3071d857f6218ddc942888ca4cf2429b832324ff`:

```text
Ruff: All checks passed!
pytest: 320 passed, 0 failed
git diff --check: clean
working tree: clean
```

The implementation was merged to `main` as merge commit `e2e1848d6882b35a5bc4488ec27829b69c1766bf`.
