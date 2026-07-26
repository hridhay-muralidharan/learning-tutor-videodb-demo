# EdTech UX Model

The generated app is a study workbench, not a marketing page.

## Product Thesis

The long-term use case is AI-enabled learning for schools, colleges, coaching programs, and institutes that cannot give every student one-on-one teacher time. In a classroom where one teacher may be responsible for 50 or more students, the app should help each learner get a more adaptive study loop while the institution keeps control of curriculum, textbooks, question banks, and video lessons.

GATE Organic Chemistry is the demo pack because public online material is available. It is not the product boundary.

Core learner loop:

1. Continue the next lesson.
2. Read the syllabus-grounded lesson card.
3. Check textbook and video evidence.
4. Attempt practice.
5. Mark confidence.
6. Review weak lessons later.

UX principles:

- Show a clear next step on the dashboard.
- Keep the course map available on desktop without competing with the next action.
- Put lesson content first on mobile.
- Track mastery over page views.
- Persist progress locally with `localStorage`.
- Add wrong, skipped, or low-confidence lessons to the review queue.
- Keep citations visible without overwhelming the learner.
- Avoid decorative hero sections, generic cards, and visual clutter.

The default learner layout should not expose every surface at once. Start uses one dominant next action with the course map below or beside it. Learn uses a focused lesson workspace with optional contextual evidence and notes. Sources are inspectable on demand, not the default center of attention. Mobile stays content-first with no horizontal scroll.

## Personalization Model

Personalization here does not mean fixed "learning styles." The app should not label a student as visual, auditory, weak, or gifted. It should let the learner and teacher adjust the conditions of learning:

- Goal: exam readiness, conceptual depth, or catch-up.
- Support level: guided, balanced, or independent.
- Session length: short, standard, or deep.
- Practice order: learn-then-practice, practice-first, or review-first.
- Source detail: compact citations or fuller source context.

These settings change the study path, prompt sequence, question load, source visibility, and review emphasis. They do not change the underlying syllabus, evidence, or correctness criteria.

## Learning Science Anchors

The UX model should stay aligned to these principles:

- Learner variability is expected. The system should provide options for engagement, representation, action, expression, and self-regulation rather than forcing one route through a lesson.
- Retrieval practice and distributed practice should be privileged over passive rereading. Practice, confidence marking, and review queues are core product surfaces, not extras.
- Formative assessment should drive the next step. Attempts, skipped questions, and low confidence should move lessons into review.
- Mastery should matter more than page completion. The progress bar should reflect durable command of lessons, not whether a card was opened.
- Cognitive load should be adjustable. Short sessions should still count; deep sessions should expose more evidence and reflection.
- Metacognition should be trained directly. The app should ask students to mark confidence, explain source support, and notice where their reasoning broke.

## Institution UX Requirements

For institutional use, the student-facing app should expose:

- curriculum map
- lesson evidence
- timestamped video moments
- practice prompts
- progress and review state
- learner personalization profile

It should not expose:

- raw textbook PDFs unless the institution chooses to publish them
- private signed URLs
- VideoDB credentials
- unpublished question-bank solutions
- unrestricted LLM-generated explanations

The source pipeline can run inside the institution's controlled environment. The generated learner app should contain only the evidence excerpts, citations, references, and readiness states that the institution intentionally permits.

## Research References

- CAST Universal Design for Learning: https://www.cast.org/what-we-do/universal-design-for-learning/
- CAST UDL Guidelines: https://udlguidelines.cast.org/
- Dunlosky et al., effective learning techniques: https://www.psychologicalscience.org/publications/journals/pspi/learning-techniques.html/comment-page-1
- IES review of formative assessment: https://nces.ed.gov/use-work/resource-library/report/descriptive-study/formative-assessment-and-elementary-school-student-academic-achievement-review-evidence
- WWC technology practice guide for postsecondary learning: https://ies.ed.gov/ncee/wwc/PracticeGuide/25
