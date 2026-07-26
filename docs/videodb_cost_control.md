# VideoDB Cost Control

VideoDB ingestion is a paid path. The learning tutor pipeline now requires a no-spend estimate and dry-run before any confirmed ingest.

## Supported GATE Modes

The public demo course supports two paid VideoDB modes under `videodb_pilot` in `course.yaml`:

- default budget: `$10`
- supported lesson count: `7` for the full Organic Chemistry pass
- scene indexing: off when `readiness.requires_scene_index: false`
- evidence mode: spoken-word transcript and timestamp search only

The default recommended lessons are course-local configuration, not generic package behavior.

Broad playlists can stay in `video_sources.json` as discovery/reference sources by setting `ingest_candidate: false`. Only exact `ready_for_ingest` candidates mapped to the requested lesson set are allowed into the paid estimate.

## Commands

```bash
python3 -m learning_tutor videos discover --course courses/gate_organic_chemistry
python3 -m learning_tutor videos estimate --course courses/gate_organic_chemistry --lessons stereochemistry,reaction_mechanisms,organic_synthesis,pericyclic_photochemistry,heterocycles,biomolecules,experimental_techniques --budget 10
python3 -m learning_tutor videos dry-run --course courses/gate_organic_chemistry --lessons stereochemistry,reaction_mechanisms,organic_synthesis,pericyclic_photochemistry,heterocycles,biomolecules,experimental_techniques --budget 10
python3 -m learning_tutor videos ingest --course courses/gate_organic_chemistry --confirm --lessons stereochemistry,reaction_mechanisms,organic_synthesis,pericyclic_photochemistry,heterocycles,biomolecules,experimental_techniques --budget 10
```

`estimate` and `dry-run` do not spend VideoDB credits. They write:

```text
courses/<course>/artifacts/videodb_cost_manifest.json
```

The manifest records the selected lessons, credit-consuming sources, estimated upload/transcription/search/storage costs, budget, rate-card version, blocked reasons, and a request signature. Confirmed ingest refuses to run if the latest successful dry-run is missing or stale.

## Hard Stops

Confirmed ingest blocks when:

- `--confirm` is missing
- the dry-run manifest is missing, blocked, or stale
- the estimate exceeds the budget
- the VideoDB API key is missing
- the VideoDB SDK is missing
- `check_usage()` cannot snapshot credits before a paid operation
- a candidate has no duration estimate
- a paid candidate cannot be confidently mapped to the requested lesson set

The live upload adapter is implemented behind these gates. It snapshots sanitized VideoDB usage before ingest, after each completed source, and at final completion.

Current public-demo full-course status:

- discovered candidates: `24`
- ready real VideoDB videos: `9`
- retained non-ready VideoDB uploads: `1`
- final resumed dry-run estimate: `$1.8897`
- final resumed actual delta: `1.9229` credits
- budget: `$10`
- scene indexing: `not_required`

## Source Boundaries

VideoDB evidence only grounds video transcript/timestamp evidence. It does not replace textbook grounding or question-bank grounding. Textbook and question-bank PDFs should be validated and indexed locally before any VideoDB spend.

Bundled demo video markers remain `demo_placeholder`. Lessons become video `source_backed` only when they have real VideoDB IDs, collection ID, uploaded status, ready spoken-word index, cached transcript segments, and timestamp-searchable evidence. Failed or partial VideoDB uploads remain `failed` or `needs_processing` and are not used as ready evidence.
