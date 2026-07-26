# Reference Flows

This document captures product patterns to borrow and avoid. It is not a visual copy brief; it is a flow and interaction brief.

## Coursera: Progress And Next Step

Source: https://blog.coursera.org/new-progress-tracking-features-on-coursera/

Pattern to borrow:

- Course dashboard shows progress.
- Course home highlights the recommended next item.
- A Start action takes the learner directly to the next video, reading, assignment, retry, or practice task.
- Learner can still navigate the full outline.

Product implication:

- Learning Tutor Start must prioritize one recommended next task.
- The course path is secondary but always available.
- Recommendation reason should be visible: last left off, review needed, weak concept, assigned work, or source setup incomplete.

Avoid:

- Treating progress as simple completion.
- Hiding review-needed work behind linear course completion.

## Udemy: Course Player

Source: https://support.udemy.com/hc/en-us/sections/206457187-Course-player

Pattern to borrow:

- Course player centers the learning object.
- Curriculum, resources, notes, Q&A, and transcripts are available from predictable controls.
- Returning learners resume where they left off.
- Notes can be timestamped and private.

Product implication:

- Lesson Workspace should center the current lesson or practice item.
- Evidence, sources, notes, and doubts belong in contextual panels or tabs, not as competing dashboard content.
- Private notes should stay local in the static app unless an institution adds authenticated syncing.

Avoid:

- Making the app feel like a video playlist.
- Letting side panels dominate the learning task.

## Khan Academy: Mastery And Practice

Source: https://support.khanacademy.org/hc/en-us/articles/360007253831-Using-self-paced-practice-and-Mastery-in-the-classroom

Pattern to borrow:

- Mastery is skill or concept based.
- Practice can move a learner between states.
- Progress is not only activity completion.
- Post-practice feedback can recommend lessons.

Product implication:

- Learning Tutor should track not started, seen, practiced, review needed, and mastered.
- Mastery should require practice or retrieval, not reading alone.
- Low-confidence or incorrect practice should send lessons to Review.

Avoid:

- Treating a opened lesson as mastered.
- Using gamified points without learning meaning.

## Moodle/LMS Dashboard

Source: https://docs.moodle.org/34/en/Dashboard

Pattern to borrow:

- Dashboard surfaces progress, required activities, deadlines, and course overview.
- Teachers and students can track required activities.

Product implication:

- Institutional deployments need assigned work and adaptive recommendations to coexist.
- Student UI must distinguish required institution tasks from suggested adaptive review.

Avoid:

- Turning the learner home into a full LMS admin dashboard.
- Showing every metric before the learner has a next action.

## CAST Universal Design For Learning

Sources:

- https://www.cast.org/resources/about-universal-design-for-learning/
- https://udlguidelines.cast.org/

Pattern to borrow:

- Offer multiple means of engagement, representation, and action/expression.
- Build learner agency rather than fixed learner typing.
- Optimize choice, relevance, support, reflection, and accessible routes.

Product implication:

- Personalization should offer adjustable support, pacing, source detail, explanation depth, practice order, and review intensity.
- The app should avoid fixed learning-style claims.

Avoid:

- "Visual learner" or "auditory learner" labels.
- Personalized paths that reduce rigor without an explicit accommodation.

## WWC / IES: Technology For Learning

Source: https://ies.ed.gov/ncee/wwc/PracticeGuide/25

Pattern to borrow:

- Use personalized and readily available digital resources.
- Foster self-regulated learning.
- Provide timely and targeted feedback.

Product implication:

- Every session should have a goal and a visible next step.
- Feedback should drive review and remediation.
- The app should explain why it recommends a topic.

Avoid:

- Feedback that only says correct or incorrect.
- Recommendations that appear without evidence from profile, progress, source coverage, or teacher assignment.

## Cross-Product Flow Contract

Learning Tutor should combine:

- Coursera's clear next action.
- Udemy's focused lesson player plus notes/resources/transcripts.
- Khan Academy's mastery and practice feedback.
- Moodle's institutional assignment awareness.
- UDL's flexible routes without fixed learning-style claims.
- WWC's self-regulation and targeted feedback requirements.

The resulting product flow is:

1. Start with one recommended action.
2. Learn in a focused workspace.
3. Practice before claiming mastery.
4. Mark confidence and receive formative feedback.
5. Review weak or stale concepts.
6. Inspect source basis when needed.
7. Adjust profile without changing source truth.
