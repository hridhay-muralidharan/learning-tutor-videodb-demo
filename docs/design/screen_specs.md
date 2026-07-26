# Screen Specs

## Global Navigation

Screens:

- Start
- Learn
- Practice
- Review
- Profile
- Sources

Rules:

- Navigation labels must stay learner-facing.
- No screen should expose institution or developer controls inside the learner flow.
- Admin and developer experiences are documented future surfaces unless explicitly approved for implementation.

## Start Screen

Primary user goal: begin or resume learning.

Primary action:

- Start lesson
- Practice now if profile says practice first
- Review now if due review is higher priority

Secondary actions:

- Adjust profile
- Select a lesson from course path

Required states:

- first-time user
- returning user
- review due
- demo/source setup pending
- no lessons available

Personalization behavior:

- Goal changes dashboard copy and recommended emphasis.
- Practice-first profile makes practice the primary action.
- Review-first profile makes review primary when review items exist.
- Short session reduces visible steps and question count.

Source behavior:

- Demo/source setup state appears below the primary action.
- Source warnings must not be styled as the main learning task.

## Profile Screen

Primary user goal: tune the study experience.

Primary action:

- Save profile automatically on selection or explicit Save profile.

Controls:

- goal
- support level
- session length
- practice order
- source detail

Required states:

- default profile
- changed profile
- reset profile

Personalization behavior:

- Changes are immediately reflected in Start and Learn.
- Choices persist with localStorage.

Guardrails:

- No fixed learning-style labels.
- No personality diagnosis.
- No claims that profile changes alter source truth.

## Learn Screen

Primary user goal: study one concept.

Primary action:

- Practice now

Secondary actions:

- Check sources
- Next lesson
- Save notes

Required states:

- source-backed lesson
- source setup pending
- missing textbook evidence
- missing video evidence
- missing question evidence

Personalization behavior:

- Guided mode shows more prompts and smaller steps.
- Independent mode reduces scaffolding.
- Full source mode exposes more source context or a stronger Sources CTA.

Source behavior:

- Syllabus anchor is always visible.
- Evidence state badge is visible near title.
- Missing evidence is a status, not a broken screen.

## Practice Screen

Primary user goal: attempt retrieval or application.

Primary action:

- Submit answer or mark confidence in static demo mode.

Secondary actions:

- Reveal source or answer after attempt.
- Try similar.
- Review concept.

Required states:

- linked question evidence
- missing question evidence
- confidence locked before attempt
- correct attempt
- incorrect attempt
- skipped or low confidence

Personalization behavior:

- Short session shows fewer questions.
- Deep session can show more prompts.
- Guided mode offers hints earlier.

Source behavior:

- Question provenance appears after attempt or inside source detail.
- Missing question-bank evidence says practice is not linked yet.
- Confidence controls remain disabled until the learner records a practice attempt.

## Review Screen

Primary user goal: recover weak or stale lessons.

Primary action:

- Review lesson

Secondary actions:

- Practice
- Mark reviewed only after a meaningful attempt

Required states:

- no review backlog
- low-confidence review
- stale review
- incomplete-source review

Personalization behavior:

- Review-first profile prioritizes this screen.
- Short sessions show a small review set.

Source behavior:

- Source-incomplete lessons can appear, but the reason must say source setup pending.

## Sources Screen

Primary user goal: inspect why the app trusts or does not trust a lesson.

Primary action:

- Return to Learn or open source detail.

Required states:

- source-backed
- demo placeholder
- source unavailable
- needs processing

Personalization behavior:

- Essential source detail shows compact source cards.
- Full source detail shows longer evidence context when available.

Source behavior:

- Never show fake page numbers, timestamps, or question years.
- Never expose raw protected material unless institution policy allows it.

## Future Institution Surface

Do not implement in the learner static app unless approved.

Future screens:

- Cohorts
- Source Library
- Assignments
- Analytics
- Settings

Primary questions:

- Which learners need intervention?
- Which concepts are weak?
- Which sources are ready?
- What should the instructor assign next?

## Future Developer Surface

Do not implement in the learner static app unless approved.

Future screens:

- Projects
- API keys
- Source ingestion
- Retrieval playground
- Logs
- Docs

Primary questions:

- Is ingestion working?
- What chunks are retrieved?
- What answer/citation behavior is produced?
- What failed and why?
