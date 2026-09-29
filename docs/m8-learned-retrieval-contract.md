# M8 Learned Semantic Retrieval Contract

## Goal

M8 connects the existing Discogs-EffNet learned audio embedding index to recommendation signals.

The existing learned stack remains unchanged:

`local track -> Discogs-EffNet -> 1280-D embedding -> persistent NumPy index -> cosine similarity`

M8 adapts that track-to-track similarity into the existing M1 `CandidateSignals.learned_score` channel.

## Boundary

M8 accepts a seed track and structured candidates:

`seed track -> learned similarity -> candidate learned_score -> M4 intent enrichment -> M1 fusion -> M2 sequencing`

This is intentionally **track-to-track** retrieval. M8 does not claim that the EffNet model understands natural-language intent.

## Similarity mapping

The existing vector index returns cosine similarity in approximately `[-1, 1]`.

M8 maps it deterministically to the fusion range:

`learned_score = clamp((cosine_similarity + 1) / 2, 0, 1)`

Missing candidate similarity keeps its existing learned score. If no prior score exists, the neutral value is `0.0`.

The seed itself is excluded from its own similarity result.

## Preservation rules

M8 must:

- preserve track IDs;
- preserve metadata, DSP, preference, novelty, and diversity signals;
- avoid mutating input candidates;
- reject duplicate candidate IDs;
- use stable deterministic candidate processing;
- ignore similarity results for tracks outside the candidate set;
- tolerate missing similarity entries without failing the recommendation;
- leave M1 fusion weights unchanged.

## Catalog integration

The existing SQLite catalog remains the source of truth.

The existing `LearnedEmbeddingService` remains responsible for:

- loading the local EffNet model;
- computing a seed embedding;
- reading the derived persistent vector index;
- returning `SimilarityResult` values.

M8 adds only the adapter that converts those results into recommendation evidence. Rebuilding the learned index remains an explicit derived-data operation.

## Non-goals

M8 does not add:

- a new embedding model;
- CLAP;
- an LLM;
- text-to-audio retrieval;
- cloud inference;
- automatic mood/language/scene classification;
- database migrations;
- new M1 fusion weights;
- changes to M2 sequencing behavior;
- automatic index rebuilding during recommendation.

## Future extension

A later text-semantic retrieval milestone may add a model capable of mapping natural-language music intent into an embedding space. That must remain a separate contract rather than being implied by M8.
