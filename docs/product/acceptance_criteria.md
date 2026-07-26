# Acceptance Criteria

## Release Gate

A learner-facing build cannot pass QA unless every applicable screen has:

- one primary user goal
- one primary action
- visible source-readiness state when evidence matters
- mobile behavior defined
- personalization behavior defined
- no unsupported generated lesson content

## Global Learner UX Criteria

- A first-time user can identify the next action in under 5 seconds.
- Desktop and mobile layouts have no horizontal scroll at 390px, 768px, and 1280px widths.
- Navigation labels are learner-facing: Start, Learn, Practice, Review, Profile, Sources.
- The app does not require reading CLI docs to test learner interactions.
- UI does not expose raw implementation concepts such as artifact filenames as primary learning content.

## Personalization Criteria

- Profile choices are plain-language and reversible.
- Profile changes affect the dashboard recommendation or lesson flow.
- No fixed learning-style labels are used.
- Guided mode provides more scaffolding.
- Independent mode reduces scaffolding but preserves evidence access.
- Short sessions reduce visible workload.
- Practice-first mode makes practice the primary next action.
- Full source detail shows more evidence context than essential mode.

## Evidence Criteria

- Syllabus anchor is visible for each lesson.
- Textbook evidence is required for conceptual readiness unless course rules explicitly mark the lesson incomplete.
- Video evidence must show VideoDB readiness when generated from real video processing.
- Placeholder video, textbook, or question evidence is labeled as placeholder or setup pending.
- The demo course cannot imply that real VideoDB processing has happened when it has not.
- Source warnings are prominent enough to prevent misunderstanding but secondary to the learner's next action during interaction testing.

## Practice And Review Criteria

- Practice attempt can update state to practiced, review needed, or mastered.
- Wrong, skipped, or low-confidence attempts send the lesson to Review.
- Review queue gives a reason for each item.
- Progress bar reflects mastered lessons only.
- Progress persists after refresh using localStorage.

## Institution Criteria

- Documentation explains where protected source files live.
- Documentation explains what generated artifacts may expose.
- VideoDB ingestion requires explicit confirmation.
- App serve and doctor never spend VideoDB credits.
- Generated learner app does not contain credentials, signed URLs, or raw protected files.

## Developer Criteria

- Generic package remains subject-agnostic.
- Course-specific data remains under `courses/<course_name>/`.
- Template customization does not require editing course artifacts.
- Any implementation change includes a QA mapping to this acceptance document.
