# Acceptance Test Matrix

Use this matrix before approving learner-facing UI changes.

| Area | Requirement | Test Case | Expected Result | Evidence | Severity |
|---|---|---|---|---|---|
| Start clarity | First screen has one primary next action | Fresh localStorage, open Start | Primary action is obvious in first viewport | Screenshot | Major |
| Demo honesty | Placeholder data is labeled | Open Start, Learn, Sources | Demo/source setup state is visible and secondary | Screenshot | Blocker |
| Source integrity | No fake citations or timestamps | Inspect all source cards | Every citation is real or labeled placeholder/unavailable | Screenshot or JSON trace | Blocker |
| Personalization | Profile changes visible behavior | Change practice order/session length | Start/Learn/Practice behavior changes predictably | Before/after screenshots | Major |
| Practice | Practice updates mastery/review | Mark confidence states | Progress/review queue updates | Browser notes | Major |
| Mastery guardrail | Mastery cannot come from page view alone | Open Practice before attempting | Confidence buttons are disabled until attempt | Browser notes | Blocker |
| Review | Review items explain why they appear | Open Review after low confidence | Item has reason and recovery action | Screenshot | Major |
| Responsive | Core flow works on mobile | Test 390x844 | No horizontal scroll, no overlap, CTA reachable | Screenshot | Major |
| Accessibility | Keyboard core flow works | Tab through Start to Practice | Focus visible, controls reachable | Manual notes | Major |
| Error state | Missing source data does not break UI | Use placeholder/missing evidence course | Honest unavailable state, no blank failure | Screenshot | Blocker |
| Product boundary | Demo subject does not leak into generic code | Run subject-leak scan | Demo specifics only in course files/artifacts/site | Command output | Major |

## Manual Test Scenarios

### Scenario 1: First-Time Learner

Steps:

1. Clear localStorage.
2. Open generated app.
3. Identify first action without using docs.
4. Start lesson.
5. Move to practice.
6. Mark confidence.

Pass criteria:

- Learner flow is Start to Learn to Practice to Confidence.
- No system internals are required.
- Demo limitations are honest.

### Scenario 2: Profile Changes Flow

Steps:

1. Open Profile.
2. Set practice order to practice first.
3. Return to Start.
4. Set session length to short.
5. Open Practice.

Pass criteria:

- Primary action changes to practice when appropriate.
- Short session reduces visible question load.
- Changes persist after refresh.

### Scenario 3: Evidence Inspection

Steps:

1. Open Sources for a lesson.
2. Inspect textbook, video, and practice evidence.
3. Compare labels to artifact data.

Pass criteria:

- Placeholder evidence is marked setup pending.
- No fake real source state appears.
- Raw protected sources are not exposed.

### Scenario 4: Review Recovery

Steps:

1. Open Practice.
2. Mark Need review.
3. Open Review.
4. Return to lesson.

Pass criteria:

- Lesson appears in Review.
- Review item explains why.
- Learner has a recovery action.

### Scenario 5: Mobile Flow

Steps:

1. Open app at 390x844.
2. Use Start, Learn, Practice, Review, Profile, Sources.

Pass criteria:

- No horizontal scroll.
- Text readable.
- Navigation tappable.
- No overlapping panels or clipped buttons.

## Source-Integrity Blocking Checks

Block release if:

- Placeholder content appears source-backed.
- App claims VideoDB processing when only bundled placeholders exist.
- App marks a video source-backed without a lesson-matched `videodb_spoken_word_search` timestamp.
- Transcript-cache or caption fallback is shown as source-backed video evidence.
- Textbook pages, video timestamps, question years, or citations are fabricated.
- Missing source data creates blank or broken screens.
- App gives unsupported conceptual explanations as if source-grounded.
- VideoDB ingest can run without a successful dry-run manifest.
- VideoDB estimated or actual spend can exceed the requested budget.
- Credit-consuming sources are not listed before confirmed ingest.
- A pilot lesson is marked video source-backed without real VideoDB IDs, transcript cache, timestamp labels, and lesson-matched VideoDB spoken-word search evidence.

## Personalization Blocking Checks

Block release if:

- Profile choices do not change visible behavior.
- Recommendations cannot be explained using profile, progress, source state, or assignment.
- App uses fixed learning-style labels.
- App claims deep personalization from unprocessed sources.
- Mastery can be achieved by opening a page only.

## Responsive And Accessibility Blocking Checks

Block release if:

- Core mobile flow has horizontal scroll.
- Primary CTA text clips or overlaps.
- Keyboard users cannot reach core controls.
- Focus states are invisible.
- Correctness or progress is color-only.
