# Wireframes

These are text wireframes for product-owner approval before implementation. They define layout and flow, not final visual styling.

## Learner Start

Purpose: tell the learner what to do next.

Desktop wireframe:

```text
+--------------------------------------------------------------+
| Course title                         Mastery progress         |
| Start | Learn | Practice | Review | Profile | Sources         |
+--------------------------------------------------------------+
|                                                              |
|  +-----------------------------------+  +------------------+  |
|  | START HERE                        |  | TODAY            |  |
|  | Current lesson title              |  | Next task        |  |
|  | Why this is recommended           |  | Review due       |  |
|  |                                   |  | Profile summary  |  |
|  | 1 Read anchor                     |  +------------------+  |
|  | 2 Check evidence                  |                        |
|  | 3 Practice                        |                        |
|  | 4 Mark confidence                 |                        |
|  |                                   |                        |
|  | [Primary action] [Adjust profile] |                        |
|  | Demo/source state, secondary      |                        |
|  +-----------------------------------+                        |
|                                                              |
|  Course path, secondary list                                  |
+--------------------------------------------------------------+
```

Mobile wireframe:

```text
+----------------------------------+
| Course title                     |
| Mastery progress                 |
| Start Learn Practice             |
| Review Profile Sources           |
+----------------------------------+
| START HERE                       |
| Current lesson title             |
| Why recommended                  |
| [Primary action]                 |
| [Adjust profile]                 |
| Demo/source state                |
| Today summary                    |
| Course path                      |
+----------------------------------+
```

Acceptance:

- One dominant primary action.
- Demo warning below primary action.
- Course path below the main start card.

## Learner Profile

Purpose: personalize the flow without technical setup.

Wireframe:

```text
+--------------------------------------------------+
| PROFILE                                          |
| Tune today's study experience                    |
|                                                  |
| Goal                                             |
| ( ) Exam readiness  ( ) Concept depth ( ) Catch up|
|                                                  |
| Support level                                    |
| ( ) Guided  ( ) Balanced  ( ) Independent        |
|                                                  |
| Session length                                   |
| ( ) Short  ( ) Standard  ( ) Deep                |
|                                                  |
| Practice order                                   |
| ( ) Learn then practice                          |
| ( ) Practice first                               |
| ( ) Review first                                 |
|                                                  |
| Source detail                                    |
| ( ) Essential  ( ) Full                          |
|                                                  |
| [Save profile] [Reset defaults]                  |
+--------------------------------------------------+
```

Acceptance:

- Plain language.
- No fixed learning-style labels.
- Changes affect Start, Learn, Practice, and Sources.

## Lesson Workspace

Purpose: help the learner study one concept at a time.

Desktop wireframe:

```text
+--------------------------------------------------------------+
| Top navigation                                               |
+--------------------------------------------------------------+
|                                                              |
| +------------------------------------+ +-------------------+ |
| | Breadcrumb and concept title       | | Lesson loop       | |
| | Source state badge                 | | Read              | |
| |                                    | | Evidence          | |
| | 1 Read                             | | Practice          | |
| | Syllabus anchor                    | | Confidence        | |
| |                                    | |                   | |
| | 2 Make sense                       | | Private notes     | |
| | Study prompt for profile           | |                   | |
| |                                    | +-------------------+ |
| | 3 Check yourself                   |                       |
| | Prompts before practice            |                       |
| |                                    |                       |
| | [Practice now] [Sources] [Next]    |                       |
| +------------------------------------+                       |
+--------------------------------------------------------------+
```

Mobile wireframe:

```text
+----------------------------------+
| Concept title                    |
| Source state                     |
| 1 Read                           |
| 2 Make sense                     |
| 3 Check yourself                 |
| [Practice now]                   |
| [Sources] [Next]                 |
| Notes collapsed                  |
+----------------------------------+
```

Acceptance:

- No sticky action bar covering content.
- Source state is visible but not the lesson's dominant element.
- Notes are available without competing with reading.

## Practice

Purpose: create retrieval, feedback, and review signals.

Wireframe:

```text
+--------------------------------------------------+
| PRACTICE: Concept title                          |
| Why this question is here                        |
|                                                  |
| Question / prompt                                |
| [Answer options or input]                        |
| [Submit] [Need a hint]                           |
|                                                  |
| After attempt:                                   |
| Feedback                                         |
| Source basis / unavailable state                 |
| [Try similar] [Review concept] [Continue]        |
|                                                  |
| Confidence                                       |
| [Need review] [Practiced] [Mastered]             |
+--------------------------------------------------+
```

Acceptance:

- Explanation is not shown before attempt unless the learner explicitly asks for a hint.
- Confidence changes review/mastery state.
- Missing question evidence is honest.

## Review Queue

Purpose: provide a recovery loop.

Wireframe:

```text
+--------------------------------------------------+
| REVIEW                                           |
| Lessons appear here because of low confidence,   |
| missed practice, stale review, or source setup.  |
|                                                  |
| Concept card                                     |
| Reason: low confidence / incomplete source       |
| Last action                                      |
| [Review lesson] [Practice]                       |
+--------------------------------------------------+
```

Acceptance:

- Review feels actionable, not punitive.
- Each item explains why it appears.

## Sources

Purpose: make trust inspectable.

Wireframe:

```text
+--------------------------------------------------+
| SOURCES: Concept title                           |
|                                                  |
| Textbook                                         |
| State: Source-backed / placeholder / unavailable |
| Citation or setup message                        |
|                                                  |
| Video                                            |
| State and timestamp if real VideoDB data exists  |
|                                                  |
| Practice                                         |
| State and source reference                       |
|                                                  |
| Course evidence map                              |
+--------------------------------------------------+
```

Acceptance:

- Placeholder states cannot be mistaken for processed evidence.
- Source detail level changes how much context is shown.
- Raw protected files are not exposed.
