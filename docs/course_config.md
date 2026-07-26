# Course Configuration

`learning_tutor` treats every course as a folder. The Python package is generic; subject-specific scope, URLs, files, lesson names, and citations live inside the course folder.

Required files:

```text
course.yaml
syllabus_sources.json
textbook_sources.json
video_sources.json
question_bank_sources.json
lesson_map.json
artifacts/
site/
```

Key rules:

- `course.yaml` sets readiness gates, app path, active scope, and missing-evidence policy.
- `course.yaml` can also set learner personalization defaults for the generated app.
- `lesson_map.json` is the syllabus-shaped lesson boundary.
- Source JSON files define where evidence comes from.
- `artifacts/` stores generated indexes and VideoDB readiness state.
- `site/` is disposable output from `python3 -m learning_tutor app generate`.

Optional personalization defaults:

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

These defaults are copied into the generated lesson plan. The learner can still adjust their local profile from the static app unless an institution customizes the template to lock settings.

To create another course:

```bash
cp -R courses/gate_organic_chemistry courses/my_course
python3 -m learning_tutor course validate --course courses/my_course
```

Then replace source files, lesson map, and labels inside `courses/my_course`. Do not edit Python code for subject-specific content.
