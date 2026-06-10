---
name: refactor-after-delivery
description: Use when AI has already produced a working first-pass implementation and the next step is to improve structure, readability, module boundaries, and maintainability without changing the intended behavior.
---

# Refactor After Delivery

Use this skill after a feature already works and the next goal is to improve code structure.

## Goal

Separate feature landing from structure improvement.

## Workflow

1. Confirm the current behavior is already working.
2. Identify structural problems:
   - oversized files
   - mixed responsibilities
   - unclear naming
   - poor extension points
3. Refactor without changing intended behavior.
4. Re-check the original behavior.

## Guidance

- The first pass optimizes for forward progress.
- The refactor pass optimizes for readability and long-term iteration.
- Prefer extracting modules by responsibility, not by arbitrary line count.

## Focus areas

- file responsibility split
- module boundaries
- naming clarity
- reduced coupling
- easier future AI edits

## Output

Return:

- what was structurally improved
- what was intentionally left unchanged
- any remaining refactor debt

## Anti-patterns

- Treating first-pass generated code as final structure
- Combining feature debugging and broad refactor in one unclear pass
- Refactoring without preserving the original behavior target
