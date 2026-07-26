# Evidence Rules

The generator is source-grounded by default.

Each lesson requires:

- syllabus anchor
- textbook evidence
- VideoDB video evidence
- readiness state
- generated UI data

The app must not invent unsupported lesson material. If evidence is missing, the generated lesson displays an incomplete state instead of filling the gap.

Default missing-evidence messages:

```text
Concept evidence incomplete. Add/index a relevant textbook source.
VideoDB evidence incomplete. Complete video ingest and verification before generating this lesson.
Practice questions not linked yet.
```

Question evidence may be optional only when `allow_missing_questions: true` is set in `course.yaml`.

For bundled demo apps, prebuilt artifacts may be used for clone-and-study behavior. For regenerated apps, run validation, indexing, VideoDB ingest, video verification, lesson assembly, and app generation in order.
