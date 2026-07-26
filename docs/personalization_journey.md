# Personalization Journey

Journey 3 is not only for developers. It is the path where a learner, teacher, or institution adapts the study experience to the learner's needs without changing the evidence base.

## Design Position

The system should personalize the learning conditions, not fabricate custom subject matter.

Personalization can change:

- sequence
- pacing
- support level
- question load
- review frequency
- amount of source context shown
- prompts that encourage reflection

Personalization must not change:

- official syllabus anchors
- source citations
- correctness criteria
- VideoDB readiness gates
- textbook grounding requirements
- protected source access rules

## Learner-Facing Profile

The generated app exposes a Learning Profile with plain choices:

- Main goal: exam readiness, concept depth, catch-up.
- Support level: guided, balanced, independent.
- Session length: short, standard, deep.
- Practice order: learn-then-practice, practice-first, review-first.
- Source detail: essential, full.

The wording should avoid labels that sound like diagnosis or ability tracking. A learner is choosing a study posture for this moment, not being permanently classified.

## Why These Controls

The controls map to learning-science principles:

- Goal and relevance support learner agency.
- Support level adjusts scaffolding and cognitive load.
- Session length makes small study loops legitimate.
- Practice order supports retrieval practice and formative assessment.
- Source detail supports both concise review and deeper evidence inspection.

The system intentionally avoids "learning styles" logic. It should not say a student is a visual learner or auditory learner. It should offer flexible routes and let evidence from practice guide the next step.

## Institution Defaults

Institutions can set defaults in `course.yaml`:

```yaml
personalization:
  enabled: true
  defaults:
    goal: exam_readiness
    supportLevel: balanced
    sessionLength: standard
    practiceOrder: learn_then_practice
    sourceDetail: essential
```

Examples:

- A remedial cohort can default to `catch_up`, `guided`, `short`.
- An exam-revision cohort can default to `exam_readiness`, `practice_first`, `standard`.
- An honors or concept-depth cohort can default to `concept_depth`, `independent`, `deep`.

Individual learners can still adjust their local profile in the app.

## Developer Hooks

Developers can extend personalization in three places:

- `course.yaml`: defaults and institution policy.
- `templates/app/app.js`: profile model, localStorage state, recommendation rules.
- `templates/app/styles.css`: density and accessibility presentation.

Future developer extensions should keep the same rule: personalization affects workflow and scaffolding, while lesson content remains source-grounded.

## Research References

- CAST Universal Design for Learning: https://www.cast.org/what-we-do/universal-design-for-learning/
- CAST UDL Guidelines: https://udlguidelines.cast.org/
- Dunlosky et al., effective learning techniques: https://www.psychologicalscience.org/publications/journals/pspi/learning-techniques.html/comment-page-1
- IES formative assessment evidence review: https://nces.ed.gov/use-work/resource-library/report/descriptive-study/formative-assessment-and-elementary-school-student-academic-achievement-review-evidence
- WWC technology practice guide: https://ies.ed.gov/ncee/wwc/PracticeGuide/25
