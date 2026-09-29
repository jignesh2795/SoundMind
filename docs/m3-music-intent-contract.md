# M3 Music Intent Contract

## Goal

Convert a natural-language music request into a structured, deterministic intent that downstream retrieval and sequencing can consume.

M3 initially defines the intent boundary, not a full language model. The first implementation uses a small explicit vocabulary and deterministic normalization. An LLM can later implement the same contract without changing downstream consumers.

## Intent model

An intent may contain:
- raw_text: original user request
- genres
- moods
- languages
- regions
- energy: normalized 0..1 target when explicitly requested
- instrumentation
- music_types: e.g. BGM, soundtrack, song
- scene: e.g. hero entry, chase, romance, suspense
- vocal_preference: any / instrumental / vocal
- novelty: any / familiar / discovery
- negative_terms: explicitly excluded characteristics
- confidence: deterministic parser confidence in 0..1

All collections are normalized, deduplicated, and deterministically ordered.

## Initial vocabulary

### Regions / languages
- South Indian / South India → region south_india
- Tamil → language tamil
- Telugu → language telugu
- Malayalam → language malayalam
- Kannada → language kannada

### Music types
- BGM / background music → bgm
- soundtrack → soundtrack

### Scenes
- hero entry / mass entry → hero_entry
- chase → chase
- battle / fight → battle
- romance / romantic → romance
- suspense / thriller → suspense
- climax → climax

### Mood / style
- dark → dark
- emotional → emotional
- sad → sad
- happy → happy
- cinematic → cinematic
- mass → mass
- folk → folk
- classical → classical
- electronic → electronic
- orchestral → orchestral

### Energy
- low / calm → 0.3
- medium / moderate → 0.5
- high / energetic → 0.8
- very high / intense → 0.95

### Vocals
- instrumental / no vocals → instrumental
- vocal / vocals → vocal

### Novelty
- something new / discovery / discover → discovery
- familiar / known / something I know → familiar

### Negative terms
- no vocals / without vocals → vocal preference instrumental
- less vocals → vocal preference instrumental with a softer constraint represented by the same preference boundary initially

## Composition rules

Multiple recognized concepts may coexist.

Example:
dark South Indian movie BGM for a hero entry
becomes approximately:
- region: south_india
- music type: bgm
- mood: dark
- scene: hero_entry

A recognized language may coexist with the South India region.

Unknown text is preserved in raw_text but does not become a fabricated structured filter.

## Determinism

For identical input:
- output must be identical
- ordering of collections must be stable
- confidence must be stable
- no network calls
- no randomness
- no LLM dependency

## Validation

Reject:
- empty or whitespace-only input
- energy outside 0..1
- confidence outside 0..1
- invalid enum values

The parser returns a valid intent even when no vocabulary terms are recognized; structured fields remain empty and confidence is 0.

## Downstream boundary

M3 intent is an input to retrieval and sequencing:
text → MusicIntent → retrieval filters/signals → M1 ranking → M2 sequencing

M3 must not directly reorder tracks or perform audio analysis.

## Explicit exclusions

Not part of the initial M3 implementation:
- LLM calls
- embeddings
- web search
- YouTube search
- metadata enrichment
- automatic translation
- arbitrary entity extraction
- sentiment analysis
- model training
