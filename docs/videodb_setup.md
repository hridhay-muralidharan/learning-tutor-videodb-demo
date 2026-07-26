# VideoDB Setup

VideoDB is mandatory when regenerating a lesson plan or producing a new course app from swapped materials.

Set one of:

```bash
export VIDEODB_API_KEY="..."
export VIDEO_DB_API_KEY="..."
```

Install the SDK:

```bash
pip install videodb
```

Credit-control commands:

- `doctor` never spends credits.
- `app serve` never spends credits.
- `app generate` never spends credits.
- `videos discover` never spends credits.
- `videos estimate` never spends credits and writes a course-local cost manifest.
- `videos dry-run` never spends credits and must pass before ingest.
- `videos ingest` can spend credits and refuses to run without `--confirm`, a fresh dry-run manifest, and a budget check.
- `videos refresh-search` can spend search credits and refuses to run without `--confirm`; it reuses existing VideoDB video IDs and does not re-upload media.
- `setup-course` runs estimate and dry-run before ingestion when `--confirm-ingest` is passed.

Full-course flow:

```bash
python3 -m learning_tutor videos estimate --course courses/gate_organic_chemistry --lessons stereochemistry,reaction_mechanisms,organic_synthesis,pericyclic_photochemistry,heterocycles,biomolecules,experimental_techniques --budget 10
python3 -m learning_tutor videos dry-run --course courses/gate_organic_chemistry --lessons stereochemistry,reaction_mechanisms,organic_synthesis,pericyclic_photochemistry,heterocycles,biomolecules,experimental_techniques --budget 10
python3 -m learning_tutor videos ingest --course courses/gate_organic_chemistry --confirm --lessons stereochemistry,reaction_mechanisms,organic_synthesis,pericyclic_photochemistry,heterocycles,biomolecules,experimental_techniques --budget 10
```

Refresh timestamp validation for already uploaded videos:

```bash
python3 -m learning_tutor videos refresh-search --course courses/gate_organic_chemistry --confirm --lessons stereochemistry,reaction_mechanisms,organic_synthesis,pericyclic_photochemistry,heterocycles,biomolecules,experimental_techniques --budget 10
```

Live ingest behavior:

- uses `videodb.connect()` with the configured key
- uses the default collection unless the course config sets a VideoDB collection ID
- uploads only planned sources that do not already have a real non-`bundled_` VideoDB ID
- runs spoken-word indexing and does not run scene indexing when `requires_scene_index: false`
- stores transcript segments and timestamped spoken-word search validation results in `artifacts/video_index.json`
- snapshots `check_usage()` before ingest, after each video, and at final completion
- stops before the next video if actual/projected spend crosses the requested budget
- records failed or partial sources as non-ready instead of labeling them source-backed

Live search-refresh behavior:

- retrieves each existing VideoDB video by ID
- runs the course-specific spoken-word search queries from `lesson_map.json`
- writes timestamped VideoDB search results back to `artifacts/video_index.json`
- records `check_usage()` before and after the refresh
- keeps transcript/cache fallback out of source-backed video evidence

See `docs/videodb_cost_control.md` for the manifest schema, hard stops, and source-state rules.

Reference playlists can remain discoverable without entering paid ingest by setting `ingest_candidate: false`. Ingested videos are explicit `type: video` sources with exact lesson IDs and `duration_seconds`.

Generation gate:

```text
app generate fails unless videos verify passes.
```

A ready video artifact needs source ID, lesson mapping, VideoDB video ID, collection ID, upload status, spoken-word index readiness, transcript segments, and timestamped `videodb_spoken_word_search` evidence for the lesson. Scene readiness is checked only when `requires_scene_index: true`.
