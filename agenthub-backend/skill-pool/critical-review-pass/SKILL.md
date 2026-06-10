---
name: critical-review-pass
description: Use after a design decision or implementation pass to force a separate critical evaluation step focused on risks, over-complexity, weak assumptions, maintainability, and future iteration cost.
---

# Critical Review Pass

Use this skill when a plan or implementation exists and needs an explicit critical review instead of simple continuation.

## Goal

Introduce a deliberate second look that challenges the current direction.

## Review targets

- design risk
- hidden coupling
- unnecessary complexity
- boundary failures
- future maintenance cost
- future AI handoff cost

## Workflow

1. Restate the current solution briefly.
2. Evaluate what could go wrong.
3. Look for simpler alternatives.
4. Identify what will be hardest to modify later.
5. Summarize keep/change/revisit recommendations.

## Review questions

- What is the biggest risk in the current approach?
- Where is the structure more complex than necessary?
- What breaks first in the next iteration?
- Would another developer or AI continue cheaply from here?

## Output

Return:

- findings
- recommended changes
- acceptable residual risks

## Anti-patterns

- Assuming a working implementation is automatically a good implementation
- Letting AI only continue the current path without reassessment
- Closing a task before a separate critical pass is done on important work
