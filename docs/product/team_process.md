# Simulated Product Team Process

This project should not move from vague idea to implementation. Learner-facing work must pass through a product-development chain.

## Roles

### Product Manager

Owns:

- product vision
- personas
- journeys
- epics and stories
- acceptance criteria
- scope boundaries
- conflict resolution between roles

### Learning Science

Owns:

- learning model
- personalization boundaries
- scaffolding rules
- retrieval and review requirements
- formative feedback requirements
- learner-safety requirements

### UX/Product Design

Owns:

- information architecture
- wireframes
- screen specs
- interaction states
- mobile behavior
- visual hierarchy
- handoff to engineering

### Engineering

Owns:

- code architecture
- implementation plan
- data contracts
- template updates
- validation and automated tests
- integration with existing generator

### QA

Owns:

- acceptance test matrix
- manual UX checks
- source-integrity checks
- personalization behavior checks
- accessibility and responsive checks
- release-blocking decisions

### Product Owner

The user acts as product owner. The user approves the product contract, design direction, and implementation scope.

## Workflow

1. PM writes or updates PRD, personas, journeys, epics, and acceptance criteria.
2. Learning Science reviews whether the proposed personalization supports real learning without unsupported claims.
3. UX creates wireframes and screen specs.
4. Product Owner approves or requests changes.
5. Engineering maps approved specs to existing code and implementation tasks.
6. Engineering implements only approved screens and flows.
7. QA tests against acceptance criteria.
8. Failed criteria return to PM, design, or engineering based on root cause.
9. Product Owner receives QA summary and screenshots before release.

## Required Handoff Artifacts

Before implementation:

- `docs/product/prd.md`
- `docs/product/personas.md`
- `docs/product/learning_journeys.md`
- `docs/product/epics_and_stories.md`
- `docs/product/acceptance_criteria.md`
- `docs/product/reference_flows.md`
- `docs/design/wireframes.md`
- `docs/design/screen_specs.md`
- `docs/qa/acceptance_test_matrix.md`

During implementation:

- engineering notes mapping each change to user stories
- screenshots for changed screens
- validation command output

Before release:

- QA acceptance matrix with pass/fail status
- source-integrity result
- responsive screenshot result
- accessibility smoke-test result

## Clarification Rules

Ask the product owner when:

- a screen has more than one possible primary action
- source evidence is missing but the UI would look authoritative
- personalization could change rigor or correctness
- institution and independent learner needs conflict
- scope expands into admin dashboards, Q&A, teacher analytics, or developer console

Do not ask when:

- a local implementation detail follows an approved pattern
- wording can be tightened without changing meaning
- a missing state can be handled honestly with an explicit unavailable message

## Product Scope

The generated learner app is the primary product surface. Institution and developer journeys are documented and supported through configuration and extension points; a full institution dashboard and developer console are outside the generated static app.
