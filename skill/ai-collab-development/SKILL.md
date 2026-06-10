---
name: ai-collab-development
description: Use when planning or executing AI-assisted software development for medium or large projects, especially when tasks should be split into small verifiable units, first-pass implementation should be separated from later refactoring, code structure should optimize both human readability and future AI navigation cost, and a dedicated critical review pass is needed after design or implementation.
---

# AI Collaboration Development

Use this skill when the work is not just "write some code", but "organize development so AI can keep contributing across multiple iterations without drifting or raising future token cost."

## Core principles

- Split work by module before assigning tasks.
- Keep each task small, single-purpose, and verifiable in the current round.
- Use two passes:
  - Pass 1: get the feature working
  - Pass 2: refactor for structure, readability, and maintainability
- Organize code for both humans and AI:
  - clear directories
  - clear file responsibilities
  - avoid keeping too much logic in one long-lived file
- Add a separate critical review pass after:
  - solution design
  - code implementation

## Workflow

1. Identify the module boundary for the request.
2. Reduce the request to one small concrete objective for this round.
3. Implement the minimum working version first.
4. Check whether the new code creates readability or navigation problems:
   - too much logic in one file
   - mixed responsibilities
   - hard for another AI to continue from directory -> file -> local change
5. If yes, schedule or perform a refactor pass after functionality is validated.
6. Run a critical review pass before closing:
   - What is the biggest design risk?
   - What part is over-complicated?
   - What is most likely to break in the next iteration?
   - Would another developer or AI be able to continue cheaply?

## Implementation guidance

### Task sizing

- Prefer one module, one behavior, one validation target.
- If a request spans multiple modules, choose the smallest end-to-end slice first.
- Avoid combining feature delivery, architecture cleanup, and broad polish in the same first pass unless the task is genuinely small.

### First-pass delivery

- Optimize for correctness and forward progress.
- Accept concentrated implementation temporarily if it helps land the feature quickly.
- Do not confuse "working" with "finished."

### Refactor pass

After the feature works, improve:

- module boundaries
- file size and responsibility split
- naming clarity
- extension points for future work
- context cost for future AI edits

### Critical review pass

Do not only continue the current plan. Pause and reassess it.

Ask explicitly:

- Is there a simpler structure?
- Is any file becoming a future bottleneck?
- Is the current design too coupled to one implementation path?
- What would make future AI-assisted modification expensive?

## Output expectations

When using this skill, prefer outputs that make the development state easy to continue:

- clearly scoped next step
- what was implemented now
- whether refactor is still needed
- review findings or residual risks

## Anti-patterns

- Giving AI a broad multi-module request without decomposition
- Treating first-pass generated code as final structure
- Optimizing only for first-generation success
- Leaving large mixed-responsibility files in place after validation
- Skipping a dedicated critical review step
