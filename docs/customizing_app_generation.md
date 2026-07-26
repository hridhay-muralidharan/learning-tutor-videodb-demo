# Customizing App Generation

Journey 3 has two tracks:

1. Non-technical personalization by learners, teachers, and institutions.
2. Developer customization of templates, source loaders, and generation rules.

The first track matters more for the product. A learner should be able to adapt the study experience without opening a code editor.

## Non-Technical Personalization

The generated app includes a local Learning Profile. The profile lets a learner choose:

- main goal: exam readiness, concept depth, or catch-up
- support level: guided, balanced, or independent
- session length: short, standard, or deep
- practice order: learn-then-practice, practice-first, or review-first
- source detail: essential or full

These settings change the study path and UI prompts. They do not rewrite lesson content, invent explanations, or bypass evidence rules.

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

Students can then personalize from the generated app. Their choices are stored locally in the browser with `localStorage`.

## Institution Personalization

For a school, college, or institute, customization usually means:

- use the institution's curriculum and lesson map
- keep licensed textbooks, question banks, and videos inside controlled systems
- generate only citation-safe learner artifacts
- choose default learner profiles for different cohorts
- let individual students adjust pace, support, and practice order
- keep the source-grounding and VideoDB gates intact

This lets the institution tailor the learning system without exposing copyrighted source material directly in the public repo or generated app.

## Developer Customization

The static app is generated from:

```text
templates/app/index.html
templates/app/styles.css
templates/app/app.js
```

Change layout, visual style, localStorage rules, or practice interactions in those templates. Then regenerate:

```bash
python3 -m learning_tutor app generate --course courses/gate_organic_chemistry
```

Keep subject-specific content out of templates. The app should read course data from `artifacts/lesson_plan.json`.

Common customizations:

- Lesson card layout: edit `templates/app/app.js`.
- Visual density and colors: edit `templates/app/styles.css`.
- Mastery rules: edit the generated state logic in `app.js` or course-level `mastery` config.
- Personalization controls: edit the profile model in `templates/app/app.js` and default values in `course.yaml`.
- New source type: add a generic loader under the matching `learning_tutor/` package and reference it from course source manifests.

Do not add subject-specific logic to templates or Python. Course-specific material belongs in `courses/<course_name>/`.
