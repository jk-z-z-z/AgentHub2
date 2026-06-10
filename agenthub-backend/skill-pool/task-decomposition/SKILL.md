---
name: task-decomposition
description: Use when a software request is too broad or spans multiple modules and needs to be reduced into small, single-purpose, verifiable tasks before implementation.
---

# Task Decomposition

Use this skill when the current request is too large to hand to AI as one implementation step.

## Goal

Turn a broad request into a sequence of small tasks that are:

- module-bounded
- single-purpose
- verifiable in the current round

## Workflow

1. Identify the affected modules.
2. Separate end-to-end scope from immediate scope.
3. Choose the smallest useful slice for the current round.
4. Define one concrete objective.
5. Define how success will be checked.

## Guidance

- Prefer one module, one behavior, one validation target.
- If the request spans frontend, backend, and infra, do not start with all three unless the slice is tiny.
- Keep cross-module work only when the request cannot be validated otherwise.

## Output

Return:

- module boundary
- current task objective
- deferred tasks
- validation target

## Anti-patterns

- One huge prompt for a full feature
- Mixing implementation, cleanup, polish, and architecture redesign in one first step
- Starting code changes before the task boundary is clear
