# agenthub-frontend

This template should help get you started developing with Vue 3 in Vite.

## Recommended IDE Setup

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Recommended Browser Setup

- Chromium-based browsers (Chrome, Edge, Brave, etc.):
  - [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd)
  - [Turn on Custom Object Formatter in Chrome DevTools](http://bit.ly/object-formatters)
- Firefox:
  - [Vue.js devtools](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)
  - [Turn on Custom Object Formatter in Firefox DevTools](https://fxdx.dev/firefox-devtools-custom-object-formatters/)

## Type Support for `.vue` Imports in TS

TypeScript cannot handle type information for `.vue` imports by default, so we replace the `tsc` CLI with `vue-tsc` for type checking. In editors, we need [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) to make the TypeScript language service aware of `.vue` types.

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Backend Integration (Dev)

The chat UI reads data from backend APIs (no hardcoded mock data).

1) Start backend:

```sh
cd /Users/youtao/Projects/AgentHub-agentscope/agenthub-backend
uv sync
uv run uvicorn agenthub_backend.main:app --reload
```

2) Seed demo data:

```sh
cd /Users/youtao/Projects/AgentHub-agentscope/agenthub-backend
uv run python scripts/seed_demo.py --base-url http://127.0.0.1:8000/api/v1
```

3) Start frontend:

```sh
cd /Users/youtao/Projects/AgentHub-agentscope/agenthub-frontend
npm install
npm run dev
```

Optional API base override:

- copy `.env.example` to `.env.local` and set `VITE_API_BASE`

## Project Setup

```sh
npm install
```

### Compile and Hot-Reload for Development

```sh
npm run dev
```

### Type-Check, Compile and Minify for Production

```sh
npm run build
```

### Lint with [ESLint](https://eslint.org/)

```sh
npm run lint
```
