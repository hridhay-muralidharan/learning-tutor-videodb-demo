# Architecture

Learning Tutor separates institution-controlled sources from learner-facing study apps.

```text
approved syllabus/textbook/video/question sources
        |
        v
course manifests in courses/<course_name>/
        |
        v
local indexes + VideoDB video evidence
        |
        v
source-grounded lesson plan
        |
        v
static personalized study app
```

## Core Boundaries

- `learning_tutor/` contains generic validation, indexing, video readiness, lesson assembly, and static app generation.
- `templates/app/` contains the reusable learner UI.
- `courses/<course_name>/` contains subject-specific configuration, sources, artifacts, and generated site output.
- Python code must not hard-code subject names, lesson titles, source URLs, textbook names, or question-bank names.

## Course Folder Model

A course folder owns:

- `course.yaml`
- `syllabus_sources.json`
- `textbook_sources.json`
- `video_sources.json`
- `question_bank_sources.json`
- `lesson_map.json`
- `artifacts/`
- `site/`

The source manifests can point to local files, public URLs, or private institution-controlled URLs. Raw protected files do not need to be published with the generated app.

## Evidence Flow

- Syllabus indexing creates lesson anchors.
- Textbook indexing creates local citation/passages or explicit artifact-only citation markers.
- Question indexing creates practice references or approved extracted prompts.
- Video discovery and ingest build VideoDB-backed video records.
- Video verification gates app generation.
- Lesson assembly merges syllabus, textbook, video, question, readiness, and personalization data.

If evidence is missing, the generated app marks the lesson incomplete instead of filling gaps with unsupported explanations.

## Learner App

The generated app is static HTML, CSS, and JavaScript. It stores learner progress and personalization locally in the browser. The default interface exposes:

- course map
- lesson view
- source/evidence panel
- video evidence panel
- practice view
- review queue
- learning profile
- notes

Institutions can host the generated `site/` through an LMS, intranet, portal, or static hosting target.

## Public Demo

`courses/gate_organic_chemistry/` demonstrates the stack with public/demo-friendly materials. It should be treated as an example course pack, not a product boundary.
