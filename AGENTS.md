# Agent Instructions

This repository is a source-grounded Learning Tutor framework for institution-ready personalized study apps.

## Product Direction

Treat the repo as one product:

- Institutions plug in approved syllabus, textbooks, video lessons, and question banks.
- The generator builds a learner-facing app with citations, readiness states, practice references, and personalization controls.
- Students personalize pace, support level, practice order, session length, and source detail.
- GATE Organic Chemistry is only the public demo course.

Keep the public story focused on institution-ready personalized learning over approved sources.

## Architecture Rules

- Generic code lives in `learning_tutor/`.
- App templates live in `templates/app/`.
- Subject-specific material lives in `courses/<course_name>/`.
- Python code must not hard-code course-specific names, URLs, lesson titles, textbook labels, or question-bank labels.
- Regenerated lesson plans require VideoDB-verified video evidence.
- Textbook grounding is mandatory for conceptual content.
- Missing evidence must be surfaced as incomplete instead of filled with invented material.

## Public Commands

Use `learning_tutor` only:

```bash
python3 -m learning_tutor doctor --course courses/gate_organic_chemistry
python3 -m learning_tutor app generate --course courses/gate_organic_chemistry
python3 -m learning_tutor app serve --course courses/gate_organic_chemistry
```

## Source Protection

Never commit:

- credentials
- raw licensed textbooks
- private question banks
- private lecture videos
- signed URLs
- institution-only source exports

Generated learner apps may include only intentionally approved excerpts, citations, timestamps, and readiness metadata.
