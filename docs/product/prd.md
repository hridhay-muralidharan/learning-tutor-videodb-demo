# Product Requirements Document

## Product Name

Learning Tutor

## Product Vision

Learning Tutor is a source-grounded personalized study workbench for institutions and independent learners. It lets a school, college, coaching program, or training institute plug in approved curriculum, textbooks, video lessons, and question banks, then generate a learner-facing app that adapts the study flow to each learner without exposing protected source material or fabricating unsupported explanations.

The GATE Organic Chemistry course is only the public demo pack. The long-term product is a reusable system for AI-enabled learning where teacher attention is scarce, student needs vary widely, and institutions must preserve curriculum control.

## Problem

Many education settings have high student-to-teacher ratios. A teacher may not be able to continuously adapt pacing, practice, explanation depth, review timing, and support level for each student. Existing LMS and course platforms usually organize content but do not always give each learner a personalized source-grounded study loop.

The learner-facing experience centers the next study action and keeps supporting evidence available within the same lesson workspace. The interface is organized around a familiar classroom flow: follow the lesson, consult the textbook, write notes, practise, and review.

## Product Principles

- One clear next step before secondary exploration.
- Personalization changes learning conditions, not source truth.
- Source evidence is visible and honest, but not visually dominant during study.
- Mastery and review matter more than page completion.
- Institution-owned material stays protected.
- Demo placeholders must be labeled as placeholders.
- Non-technical users can personalize without editing configuration files.
- Developers can customize templates and generation logic after the learner product is coherent.

## Target Personas

- Independent learner: clones the repo, opens the demo app, wants to test and study without understanding the pipeline.
- Student in an institution: receives a generated course app through an LMS, portal, or intranet.
- Teacher or instructor: wants students to follow the approved curriculum while getting adaptive practice and review.
- Institution admin: manages protected textbooks, videos, question banks, VideoDB credentials, and source access rules.
- Developer or systems builder: extends the generic generator, templates, source loaders, and institution integrations.

## V1 Scope

V1 must support:

- Static learner app generated from course artifacts.
- Course dashboard with one primary next action.
- Learner profile for non-technical personalization.
- Focused lesson loop: read anchor, inspect evidence when needed, practice, mark confidence, review later.
- Practice cards and formative confidence feedback.
- Review queue driven by low confidence, missed/skipped practice, stale practice, or incomplete source setup.
- Source library that distinguishes real evidence from demo placeholders.
- Institutional source-protection language and configuration path.
- Developer customization path documented separately from learner personalization.

## V1 Non-Goals

- No authenticated accounts.
- No cloud progress sync.
- No teacher analytics dashboard.
- No real-time tutoring chatbot.
- No auto-generated conceptual explanations without cited evidence.
- No claim that the demo GATE course is fully VideoDB/textbook/question-bank grounded until those processes are actually run.
- No fixed "learning styles" labels.

## Success Criteria

- A first-time learner knows what to click first within 5 seconds.
- The first viewport on desktop and mobile shows the next lesson and one primary action.
- A learner can complete one full loop from Start to Learn to Practice to Confidence to Review without opening JSON or CLI docs.
- The learner profile changes the flow in visible ways: session length, support level, practice order, and source detail.
- Demo placeholder evidence is never presented as real processed evidence.
- A teacher or institution can understand where protected materials live and what is safe to expose.
- A developer can identify where to change templates or generator logic without mixing subject data into generic code.

## Product References

- Coursera progress tracking emphasizes progress bars and a recommended next item with a Start action: https://blog.coursera.org/new-progress-tracking-features-on-coursera/
- Udemy course player groups curriculum, resources, notes, Q&A, transcripts, and return-to-where-you-left-off behavior around a focused player: https://support.udemy.com/hc/en-us/sections/206457187-Course-player
- Khan Academy mastery uses skill states, practice, level changes, and recommended lessons after performance: https://support.khanacademy.org/hc/en-us/articles/360007253831-Using-self-paced-practice-and-Mastery-in-the-classroom
- Moodle dashboard organizes progress, upcoming tasks, and course overview for LMS users: https://docs.moodle.org/34/en/Dashboard
- CAST UDL frames personalization as flexible options for engagement, representation, action, and expression: https://www.cast.org/resources/about-universal-design-for-learning/
- WWC technology guidance recommends personalized resources, self-regulated learning supports, and targeted feedback: https://ies.ed.gov/ncee/wwc/PracticeGuide/25

## Product Development Gate

No additional learner-facing UI work should proceed until the relevant screen has:

- user story
- acceptance criteria
- wireframe description
- source/evidence behavior
- personalization behavior
- QA test case
