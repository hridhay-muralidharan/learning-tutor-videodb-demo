# Learning Tutor

Learning Tutor is a source-grounded study-app generator for institutions and learners.

Schools, colleges, coaching programs, and training teams can plug in approved syllabus files, textbooks, video lessons, and question banks, then generate a learner-facing app that supports personalized pacing, support level, practice order, review, and source visibility. The system is designed for environments where one teacher may support many students, and where licensed learning material must remain protected.

The bundled **GATE Organic Chemistry** course is the public demo pack because public/demo-friendly resources are available. It is not the product boundary.

## Use The Demo App

This path uses the prebuilt static app. It does not regenerate lesson plans, ingest videos, or spend VideoDB credits.

```bash
python3 -m learning_tutor doctor --course courses/gate_organic_chemistry
python3 -m learning_tutor app serve --course courses/gate_organic_chemistry
```

Open the local URL printed by the server. In the app, use the **Profile** panel to personalize:

- main goal
- support level
- session length
- practice order
- source detail

Use the local server URL for review. Opening `site/index.html` directly as a `file://` page can prevent YouTube embeds from playing even when the timestamped source link is valid.

## Build An Institutional Course

Copy the demo course folder, replace the source manifests with institution-approved materials, validate, then run setup with explicit VideoDB confirmation:

```bash
cp -R courses/gate_organic_chemistry courses/my_course
python3 -m learning_tutor course validate --course courses/my_course
python3 -m learning_tutor videos estimate --course courses/my_course --budget 10
python3 -m learning_tutor videos dry-run --course courses/my_course --budget 10
python3 -m learning_tutor setup-course --course courses/my_course --confirm-ingest --budget 10
```

Course-specific material belongs in `courses/<course_name>/`. Generic code lives in `learning_tutor/`; app templates live in `templates/app/`.

## VideoDB Organic Chemistry Path

VideoDB is used as the video intelligence layer, not as a decorative integration. The app uses VideoDB spoken-word search to turn approved long-form lecture videos into lesson-matched board moments. A video card is treated as source-backed only when it has a real VideoDB video ID, ready spoken-word indexing, a timestamped VideoDB search result, and a lesson-specific topical match. Caption or transcript fallback is not promoted to source-backed video evidence.

Lesson assembly now runs through a cross-source evidence graph. Each lesson defines concept threads, the graph indexes syllabus/textbook/video/question evidence against those threads, and the app selects the strongest shared thread across source types. This prevents a broad topic match, such as a stereochemistry video on Walden inversion, from being presented beside textbook/question evidence about enantiomers and specific rotation.

The public GATE Organic Chemistry pack includes a completed real VideoDB video pass for all seven Organic Chemistry lessons:

- `stereochemistry`
- `reaction_mechanisms`
- `organic_synthesis`
- `pericyclic_photochemistry`
- `heterocycles`
- `biomolecules`
- `experimental_techniques`

The full-course path uses the seven lesson list below. No-spend checks:

```bash
python3 -m learning_tutor videos estimate --course courses/gate_organic_chemistry --lessons stereochemistry,reaction_mechanisms,organic_synthesis,pericyclic_photochemistry,heterocycles,biomolecules,experimental_techniques --budget 10
python3 -m learning_tutor videos dry-run --course courses/gate_organic_chemistry --lessons stereochemistry,reaction_mechanisms,organic_synthesis,pericyclic_photochemistry,heterocycles,biomolecules,experimental_techniques --budget 10
```

Paid ingest path:

```bash
python3 -m learning_tutor videos ingest --course courses/gate_organic_chemistry --confirm --lessons stereochemistry,reaction_mechanisms,organic_synthesis,pericyclic_photochemistry,heterocycles,biomolecules,experimental_techniques --budget 10
```

Refresh search validation for already uploaded videos without re-uploading:

```bash
python3 -m learning_tutor videos refresh-search --course courses/gate_organic_chemistry --confirm --lessons stereochemistry,reaction_mechanisms,organic_synthesis,pericyclic_photochemistry,heterocycles,biomolecules,experimental_techniques --budget 10
```

`videos ingest` uploads only planned, not-yet-ingested sources after a fresh successful dry-run, snapshots VideoDB usage before ingest and after each video, indexes spoken words, caches transcript segments, stores timestamped search-validation results, and stops if actual/projected spend crosses the budget. `videos refresh-search` re-runs live VideoDB spoken-word searches against already uploaded videos and records before/after usage snapshots. Scene indexing is off for this course because `requires_scene_index: false`.

## Source Protection Model

Institution-controlled environments can keep raw source files private:

- licensed textbook PDFs
- question banks and solution keys
- private lecture recordings
- signed media URLs
- VideoDB API keys

The generated learner app should expose only approved excerpts, citations, timestamps, readiness states, and personalization controls.

## CLI Reference

```bash
python3 -m learning_tutor doctor --course courses/gate_organic_chemistry
python3 -m learning_tutor course validate --course courses/gate_organic_chemistry
python3 -m learning_tutor syllabus index --course courses/gate_organic_chemistry
python3 -m learning_tutor textbooks index --course courses/gate_organic_chemistry
python3 -m learning_tutor questions index --course courses/gate_organic_chemistry
python3 -m learning_tutor videos discover --course courses/gate_organic_chemistry
python3 -m learning_tutor videos estimate --course courses/gate_organic_chemistry --lessons stereochemistry,reaction_mechanisms,organic_synthesis,pericyclic_photochemistry,heterocycles,biomolecules,experimental_techniques --budget 10
python3 -m learning_tutor videos dry-run --course courses/gate_organic_chemistry --lessons stereochemistry,reaction_mechanisms,organic_synthesis,pericyclic_photochemistry,heterocycles,biomolecules,experimental_techniques --budget 10
python3 -m learning_tutor videos ingest --course courses/gate_organic_chemistry --confirm --lessons stereochemistry,reaction_mechanisms,organic_synthesis,pericyclic_photochemistry,heterocycles,biomolecules,experimental_techniques --budget 10
python3 -m learning_tutor videos refresh-search --course courses/gate_organic_chemistry --confirm --lessons stereochemistry,reaction_mechanisms,organic_synthesis,pericyclic_photochemistry,heterocycles,biomolecules,experimental_techniques --budget 10
python3 -m learning_tutor graph build --course courses/gate_organic_chemistry
python3 -m learning_tutor graph verify --course courses/gate_organic_chemistry
python3 -m learning_tutor videos verify --course courses/gate_organic_chemistry
python3 -m learning_tutor app generate --course courses/gate_organic_chemistry
python3 -m learning_tutor app serve --course courses/gate_organic_chemistry
```

Credit-control rules:

- `doctor`, `app serve`, `app generate`, and `videos discover` do not spend VideoDB credits.
- `videos ingest` requires `--confirm`.
- `videos refresh-search` requires `--confirm` because it calls live VideoDB search, but it does not re-upload videos.
- `setup-course` requires `--confirm-ingest` before ingestion.
- `app generate` fails if video verification fails.

## Documentation

- [Product requirements](docs/product/prd.md)
- [Team process](docs/product/team_process.md)
- [Personas](docs/product/personas.md)
- [Learning journeys](docs/product/learning_journeys.md)
- [Epics and stories](docs/product/epics_and_stories.md)
- [Acceptance criteria](docs/product/acceptance_criteria.md)
- [Reference flows](docs/product/reference_flows.md)
- [Wireframes](docs/design/wireframes.md)
- [Screen specs](docs/design/screen_specs.md)
- [UI direction](docs/design/ui_direction.md)
- [QA acceptance matrix](docs/qa/acceptance_test_matrix.md)
- [Implementation QA report](docs/qa/implementation_qa_report.md)
- [Engineering implementation plan](docs/engineering/implementation_plan.md)
- [Architecture](docs/architecture.md)
- [Course config](docs/course_config.md)
- [Institution deployment](docs/institution_deployment.md)
- [Personalization journey](docs/personalization_journey.md)
- [Evidence rules](docs/evidence_rules.md)
- [VideoDB setup](docs/videodb_setup.md)
- [Customizing app generation](docs/customizing_app_generation.md)
- [EdTech UX model](docs/edtech_ux_model.md)

## Requirements

- Python 3.10+
- PyYAML
- VideoDB SDK for live video ingestion/indexing
- `yt-dlp` only when playlist discovery is needed

Install dependencies:

```bash
pip install -r requirements.txt
```

Set credentials only in local/private environments:

```bash
cp .env.example .env
# Add VIDEODB_API_KEY or VIDEO_DB_API_KEY
```

Do not commit credentials, private licensed sources, private signed URLs, or institution-only materials.

## Evidence and Privacy

- Real: generic course validation, no-spend VideoDB estimate/dry-run gates, live VideoDB adapter implementation, VideoDB search-refresh for already uploaded videos, evidence graph build/verify, completed real VideoDB spoken-word search evidence across all seven GATE Organic Chemistry lessons, OpenStax textbook section evidence, official GATE Chemistry question-paper evidence, regenerated classroom-style static app, source-state guardrails, and browser/unit QA.
- Real textbook source: OpenStax Organic Chemistry, John McMurry, 10th edition, with curated section evidence and source URLs under CC BY-NC-SA 4.0.
- Real question-bank source: official GATE Chemistry 2025 and 2024 question papers and answer keys from the IIT/GATE download pages.
- Active real ready video IDs: `m-z-019f9f53-86c6-79f3-8304-d9dabec3e2b5`, `m-z-019f9deb-0e6e-7533-b064-09fa80d54428`, `m-z-019f9df7-8edd-79a1-869d-a5ceb34bcea6`, `m-z-019f9e12-1767-77b0-83b1-76e80dae1106`, `m-z-019f9f35-9950-79a0-9630-6046f9c7f2e0`, `m-z-019f9e34-c978-7652-8e88-6a9acb307a35`, `m-z-019f9e38-872e-7cc2-ac64-b6f1c50fd991`, `m-z-019f9e39-aa4f-7ad1-b6fc-2c4713d68eed`, `m-z-019f9e3a-dd9e-7d00-a8c4-37ad5b417ce3`.
- Protected source material is not included: `.env`, VideoDB credentials, private licensed PDFs, private question banks, private lecture media, signed URLs, and institution-only source exports.
