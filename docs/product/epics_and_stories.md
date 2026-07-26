# Epics And Stories

## Epic 1: Learner Start Experience

### Story 1.1

As a learner, I want to open the app and immediately know what to do next, so I can begin studying without understanding the source pipeline.

Acceptance criteria:

- First screen shows exactly one primary learning action.
- Course map is available but visually secondary.
- Demo/source warning is visible but does not compete with the primary action.
- Mobile first viewport contains the course title, mastery state, current lesson, and primary action.

### Story 1.2

As a returning learner, I want the app to continue from my last useful learning state, so I do not restart from the beginning every time.

Acceptance criteria:

- Last active lesson persists locally.
- Mastery state persists after refresh.
- Review-needed lessons influence the next recommended action.

## Epic 2: Non-Technical Personalization

### Story 2.1

As a learner, I want to adjust how the app supports me today, so the experience fits my goal, pace, confidence, and available time.

Acceptance criteria:

- Profile screen exposes goal, support level, session length, practice order, and source detail.
- Choices use plain language.
- No option labels the learner as weak, slow, gifted, visual, auditory, or similar.
- Profile changes visibly alter the Start and Lesson flows.

### Story 2.2

As an institution, I want to set cohort defaults, so students begin with an appropriate study posture while still being able to adjust locally.

Acceptance criteria:

- `course.yaml` can define personalization defaults.
- Generated app reads defaults.
- Local learner choices override defaults in localStorage.

## Epic 3: Focused Lesson Loop

### Story 3.1

As a learner, I want each lesson to guide me through a small loop, so I can make progress even in short sessions.

Acceptance criteria:

- Lesson presents read, evidence, practice, confidence, next-step sequence.
- The sequence is visible without requiring a tutorial.
- Action buttons do not overlay or hide lesson content.
- Short session profile reduces visible workload.

### Story 3.2

As a learner, I want practice to update my review path, so the app helps me revisit weak areas.

Acceptance criteria:

- Marking low confidence adds the lesson to Review.
- Marking mastered updates mastery progress.
- Practice-first profile starts on practice or makes practice the primary action.

## Epic 4: Evidence Trust

### Story 4.1

As a learner, I want to know whether lesson content is grounded in real sources, so I can trust what I am studying.

Acceptance criteria:

- Source view separates syllabus, textbook, video, and question evidence.
- Placeholder or artifact-only evidence is labeled as setup pending.
- Missing textbook evidence shows a concept-evidence warning.
- Missing VideoDB evidence shows an ingest/verification warning.

### Story 4.2

As an institution, I want protected material to remain private, so the generated app can be distributed safely.

Acceptance criteria:

- Raw PDFs, signed URLs, credentials, and unpublished solution keys are not required in the generated app.
- Generated app uses approved excerpts, citations, timestamps, and readiness metadata only.
- Documentation explains public demo mode versus private institutional deployment.

## Epic 5: Practice And Review

### Story 5.1

As a learner, I want practice feedback to be formative, so it guides what I should review instead of only grading me.

Acceptance criteria:

- Practice cards support answer reveal or source reference.
- Confidence choices update lesson state.
- Review queue explains why each lesson appears.

### Story 5.2

As a teacher, I want practice state to reflect mastery, so completion does not hide weak understanding.

Acceptance criteria:

- Progress bar is based on mastery, not opened pages.
- Seen, practiced, review-needed, and mastered are distinct states.
- Low confidence can lower or prevent mastery.

## Epic 6: Institutional Setup

### Story 6.1

As an admin, I want generation to stop when required source processing is incomplete, so students are not shown unsupported lessons.

Acceptance criteria:

- App generation fails if video verification fails when video evidence is required.
- Missing textbook evidence marks lesson incomplete or fails generation according to course rules.
- Missing question evidence follows `allow_missing_questions`.
- VideoDB credit-spending commands require explicit confirmation.

## Epic 7: Developer Customization

### Story 7.1

As a developer, I want to customize templates and planner behavior, so I can adapt the product without editing course-specific data.

Acceptance criteria:

- Generic code contains no subject-specific demo terms.
- Templates are documented as the UI customization layer.
- Course files contain subject data.
- Tests include generic-code leakage checks.
