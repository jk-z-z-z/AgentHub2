---
name: ai-development-orchestrator
description: Use as the top-level entry skill for AI-assisted software development when work may require task decomposition, first-pass implementation, post-delivery refactoring, codebase organization improvements, or a separate critical review pass.
---

# AI Development Orchestrator

Use this skill as the default entry point for medium or large AI-assisted development work.

Its job is to decide which specialized skill should be used next and in what order.

## Purpose

Coordinate AI-assisted development so work stays:

- small enough to control
- structured enough to maintain
- reviewable enough to trust

## Available follow-up skills

- `task-decomposition`
  Use when the request is broad, spans multiple modules, or does not yet have a small verifiable target.

- `refactor-after-delivery`
  Use when the feature already works and the next step is structural improvement.

- `ai-codebase-organization`
  Use when the code layout increases navigation cost for humans or future AI edits.

- `critical-review-pass`
  Use when a design or implementation exists and needs an explicit second-pass challenge.

## Routing workflow

1. Classify the current request.
2. Decide whether the work is:
   - under-scoped
   - implementation-ready
   - structurally messy
   - review-ready
3. Select the next skill.
4. If needed, chain multiple skills in order.

## Recommended ordering

### Case 1: Request is too large

Use:

1. `task-decomposition`
2. implementation
3. `critical-review-pass`

### Case 2: Request is clear and small

Use:

1. implementation
2. `critical-review-pass`

### Case 3: Feature works but code quality is weak

Use:

1. `refactor-after-delivery`
2. `ai-codebase-organization`
3. `critical-review-pass`

### Case 4: Codebase is hard to navigate

Use:

1. `ai-codebase-organization`
2. `critical-review-pass`

## Decision rules

- If scope is unclear, decompose before implementing.
- If behavior is not landed yet, prioritize working delivery first.
- If behavior is landed, separate cleanup into a later pass.
- If file structure raises future token cost, organize code before complexity compounds.
- If an important plan or implementation was produced, run a critical review before closing.

## Output expectations

When using this skill, state:

- current development stage
- selected next skill
- why that skill is the right next step
- whether more follow-up passes are still needed

## Anti-patterns

- Jumping into implementation when the task boundary is still broad
- Treating first-pass output as final
- Skipping dedicated review on important work
- Letting code organization decay across multiple AI-generated iterations
