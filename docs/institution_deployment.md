# Institution Deployment Model

This repository should be read as a small contribution toward AI-enabled learning systems for schools, colleges, coaching programs, and training institutes.

The institutional problem is not that students need another generic chatbot. The problem is that many classrooms operate with a high student-to-teacher ratio, often 50:1 or higher, while students vary widely in pace, confidence, background knowledge, language comfort, and revision needs.

The system is designed so an institution can plug in its own curriculum, textbooks, question banks, and videos, then expose students to a personalized study interface grounded in those approved sources.

## Separation Of Concerns

Institution-controlled layer:

- curriculum and syllabus
- textbook PDFs or licensed digital sources
- question banks and solution keys
- video lessons and lecture recordings
- VideoDB credentials and ingestion jobs
- source access rules

Generated learner layer:

- course map
- lesson readiness
- citation-safe source excerpts
- timestamped video evidence
- practice references
- progress state
- personalization profile

Generic engine layer:

- source validation
- indexing
- VideoDB discovery, ingest gates, and verification
- lesson assembly
- static app generation
- templates and local learner-state logic

## Copyright And Source Protection

The repo should not require institutions to publish copyrighted textbooks, private question banks, or internal lecture videos.

Supported patterns:

- Keep raw source files inside a private course folder or institutional storage.
- Use private/signed URLs only during ingestion or indexing.
- Store only approved excerpts, citations, page references, timestamps, and readiness metadata in generated artifacts.
- Run generation inside the institution's controlled environment.
- Publish the static app only with the level of source detail the institution permits.

The GATE Organic Chemistry pack uses public/demo-friendly references because it is a submission proof. A private college deployment should not copy that public-source assumption.

## Personalization Boundaries

Student personalization should be learner-safe:

- It should adapt pace, support, review, practice order, and source detail.
- It should make weak areas visible without stigmatizing the learner.
- It should preserve teacher and institution authority over curriculum and correctness.
- It should avoid unsupported labels such as fixed learning styles.
- It should keep progress data local unless an institution deliberately adds authenticated syncing.

## Deployment Paths

Small/local deployment:

```bash
python3 -m learning_tutor app generate --course courses/my_course
python3 -m learning_tutor app serve --course courses/my_course
```

Institutional deployment:

1. Create a private course folder.
2. Add syllabus, textbook, video, and question-bank manifests.
3. Index sources inside the controlled environment.
4. Ingest videos through VideoDB with explicit confirmation.
5. Verify lesson-video-transcript readiness.
6. Generate the static learner app.
7. Host the generated `site/` through the institution's LMS, portal, or intranet.
8. Keep source PDFs, private URLs, and API keys outside the public app.

## Future Institution Features

Useful next extensions:

- authenticated learner profiles
- teacher dashboard over aggregate weak areas
- LMS integration
- cohort-level default profiles
- role-based source access
- privacy-preserving progress sync
- institution-managed question attempts
- review scheduling across subjects

These should be added without weakening the core rule: generated learning content must stay traceable to approved institutional sources.
