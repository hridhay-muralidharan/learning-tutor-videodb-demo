# Learning Journeys

## Journey 1: Open Demo And Test Interactions

### User

Independent learner or evaluator.

### Flow

1. Run `doctor`.
2. Run `app serve`.
3. Open the local URL.
4. Land on Start.
5. See one primary next action.
6. Start the first lesson.
7. Practice.
8. Mark confidence.
9. See progress or review update.

### Product Requirements

- The app must clearly say the GATE course is a demo scaffold if source evidence is placeholder-based.
- Demo warnings must not block interaction testing.
- The learner must not need VideoDB setup for static interaction testing.
- The learner must not be told that placeholder evidence is real processed evidence.

## Journey 2: Personalize As A Non-Technical Learner

### User

Independent learner or institutional student.

### Flow

1. Open Profile.
2. Choose goal, support level, session length, practice order, and source detail.
3. Return to Start.
4. See the next task and lesson loop adapt.
5. Continue studying with the chosen flow.

### Product Requirements

- Profile controls use plain language.
- No learner is labeled by ability, diagnosis, or fixed learning style.
- Changes must affect visible behavior, not only stored metadata.
- Reset or change profile must be easy.

## Journey 3: Study One Lesson

### User

Learner.

### Flow

1. Start lesson.
2. Read syllabus anchor and source-grounded study prompt.
3. Optionally inspect evidence.
4. Try practice.
5. Reveal answer or source reference when available.
6. Mark confidence.
7. Move to next lesson or review queue.

### Product Requirements

- Lesson view has one dominant learning task at a time.
- Evidence is accessible but not scattered across competing panels.
- Missing evidence states are clear.
- Practice and confidence update local progress.

## Journey 4: Institutional Course Generation

### User

Teacher, admin, or academic technology team.

### Flow

1. Copy course folder.
2. Replace manifests and protected sources.
3. Validate course.
4. Index syllabus, textbooks, and question banks.
5. Discover and ingest videos with explicit confirmation.
6. Verify videos.
7. Generate learner app.
8. Host generated app through LMS, portal, or intranet.

### Product Requirements

- VideoDB ingestion requires explicit confirmation.
- App generation fails if required video verification fails.
- Protected raw sources do not need to be committed or published.
- Generated app contains only approved excerpts, references, and readiness metadata.

## Journey 5: Developer Customization

### User

Developer or systems builder.

### Flow

1. Read architecture and product docs.
2. Choose the customization layer: course config, template, source loader, planner, or deployment integration.
3. Modify generic code or templates without changing subject data.
4. Run validation and QA.
5. Regenerate app.

### Product Requirements

- Developer journey is separate from learner profile.
- Code should stay subject-agnostic.
- Any new generation behavior must preserve evidence rules.
- QA must include source integrity and UI acceptance checks.
