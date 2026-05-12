# Ideation Context Hub Frontend

Vite React + shadcn frontend for the monorepo. FastAPI serves the production build from `frontend/dist`.

## Commands

```bash
npm install
npm run dev
npm run lint
npm run build
```

From the repository root, use:

```bash
npm run frontend:dev
npm run frontend:lint
npm run frontend:build
```

## UI Surfaces

- Multi-source ingestion for Notion, GitHub, Slack, Linear, MCP output, direct links, and file uploads.
- Graph Studio for workflow-style source/card/relation inspection.
- Obsidian Graph for file-map style exploration with search, group toggles, local depth, zoom, pan, node drag, node sizing, and link distance controls.
- Grounded LLM Search for retrieving cards/chunks and generating source-backed answers.
