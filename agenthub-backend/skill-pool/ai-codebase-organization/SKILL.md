---
name: ai-codebase-organization
description: Use when organizing or refactoring a codebase so it is easier for both humans and future AI runs to navigate, load partially, and modify with lower context cost.
---

# AI Codebase Organization

Use this skill when code organization should support both human readability and future AI-assisted development.

## Goal

Create a code layout that lets an agent move from:

directory -> target file -> local change

without needing excessive full-file or full-project loading.

## Principles

- Clear directory structure
- Clear file ownership
- Avoid long-lived mixed-responsibility files
- Prefer local reasoning over whole-file dependence

## Workflow

1. Inspect the directory structure first.
2. Identify files that force high-context loading.
3. Split by responsibility where stable boundaries exist.
4. Keep related logic near each other, but not collapsed into one bottleneck file.

## What to optimize

- human readability
- lower token cost for future AI edits
- easier local patching
- clearer ownership of logic

## Output

Return:

- structure problems found
- organization changes made
- future hotspots that may still need splitting

## Anti-patterns

- Keeping everything in one file because first-generation output looked smoother
- Deep coupling that forces global reloads for small edits
- Directory layouts that hide real module boundaries
