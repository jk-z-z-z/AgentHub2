# Frontend Structure

This frontend now follows the `AgentHub2`-style Vue structure.

## Top-Level Folders

- `src/api/`: HTTP clients and API wrappers
- `src/components/`: reusable view components
- `src/layouts/`: route-level layouts
- `src/pages/`: route pages
- `src/router/`: vue-router setup
- `src/styles/`: global styles and tokens
- `src/types/`: shared types

## Conventions

- Use `Element Plus` for UI components.
- Keep route pages thin and move composition into colocated components.
- Keep raw HTTP details inside `src/api/`.
