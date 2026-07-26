# Engineering Implementation Plan

This plan is the engineering handoff after PM, learning-science, UX, and QA definition. It should be executed only after product-owner approval of the product/design docs.

## Current Codebase Assessment

Likely reusable:

- `learning_tutor/` package boundary.
- Course folder structure under `courses/<course_name>/`.
- Static app generation through `learning_tutor app generate`.
- Template system under `templates/app/`.
- Local progress and profile persistence in `localStorage`.
- Placeholder source-state detection added to the generated app.
- CLI gates for validation, VideoDB verification, and app serving.

Needs redesign or tightening:

- Generated learner UI must be rebuilt from approved screen specs, not ad hoc layout preference.
- Personalization needs clearer visible behavior and test coverage.
- Review reasons should be explicit, not just inferred from state.
- Source cards should use consistent states: source-backed, demo placeholder, source unavailable, needs processing.
- Static demo mode should be honest on every screen.

Out of scope for immediate implementation unless approved:

- Full institution dashboard.
- Developer console.
- Real Q&A/chat interface.
- Teacher analytics.
- Authenticated progress sync.

## Implementation Sequence

### Phase 1: Data Contract

Goal: make UI states explicit in generated data.

Tasks:

- Add normalized source state fields to lesson plan output.
- Add review reason fields derived from confidence, practice, stale state, or source setup.
- Add personalization defaults and labels from `course.yaml`.
- Preserve demo placeholder flags from artifacts.

Acceptance mapping:

- `docs/product/acceptance_criteria.md` evidence criteria.
- `docs/qa/acceptance_test_matrix.md` source-integrity checks.

### Phase 2: Learner Shell

Goal: implement approved learner navigation and screen structure.

Tasks:

- Keep learner screens limited to Start, Learn, Practice, Review, Profile, Sources.
- Ensure Start screen has one primary next action.
- Ensure Learn screen centers the lesson loop.
- Ensure Sources screen is inspectable on demand.

Acceptance mapping:

- `docs/design/wireframes.md`
- `docs/design/screen_specs.md`

### Phase 3: Personalization Behavior

Goal: make profile changes visibly alter the study flow.

Tasks:

- Practice-first profile changes Start primary action.
- Review-first profile prioritizes review when review items exist.
- Short session reduces visible question count and lesson steps.
- Guided mode adds prompts or hints.
- Independent mode reduces scaffolding while keeping sources available.
- Full source detail expands source cards.

Acceptance mapping:

- `docs/product/epics_and_stories.md` Epic 2.
- `docs/qa/acceptance_test_matrix.md` personalization checks.

### Phase 4: Practice And Review

Goal: make formative feedback and review queue behavior explicit.

Tasks:

- Record confidence state.
- Send low-confidence lessons to Review.
- Display review reason.
- Prevent mastery from page-open only.
- Show placeholder practice warning when question-bank evidence is missing.

Acceptance mapping:

- `docs/product/epics_and_stories.md` Epic 5.
- `docs/product/acceptance_criteria.md` practice and review criteria.

### Phase 5: QA And Screenshots

Goal: verify the implementation against product criteria.

Tasks:

- Run CLI validation and unit tests.
- Run browser interaction checks for Start, Learn, Practice, Review, Profile, Sources.
- Capture desktop and mobile screenshots.
- Check mobile no horizontal scroll at 390px.
- Run subject-leak scan outside course artifacts.
- Confirm demo placeholder states.

Acceptance mapping:

- `docs/qa/acceptance_test_matrix.md`

## Engineering Stop Conditions

Stop and ask product owner if:

- a screen needs more than one primary CTA
- Q&A/chat becomes necessary for the learner flow
- source data is missing but the design would imply source-backed content
- institution dashboard or developer console is requested for the static learner app
- personalization would alter correctness, curriculum, or rigor

## Minimum Definition Of Done

- Implementation maps to documented stories and screen specs.
- Generated demo app can be used for interaction testing.
- Demo app clearly states that source processing is pending where applicable.
- Unit tests pass.
- Browser responsive checks pass.
- QA acceptance matrix is updated with pass/fail evidence.
