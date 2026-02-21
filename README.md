# DataLens

Upload a CSV, ask questions in natural language, get answers with auto-generated visualizations.

## Quick Start

```bash
cp .env.example .env   # add your LiteLLM API key
docker compose up -d
# open http://localhost
```

## Architecture

Four Docker services behind nginx:

- **Frontend** — React 19, TypeScript, Tailwind CSS v4, Recharts
- **API** — FastAPI with a LangGraph ReAct agent (Claude Sonnet via LiteLLM)
- **PostgreSQL 18 + pg_duckdb** — single database for app state and analytical queries
- **MinIO** — S3-compatible object storage for uploaded CSVs

Users upload a CSV, which is ingested via DuckDB's `read_csv()`. A LangGraph agent interprets questions, generates read-only SQL, and streams structured responses (text + visualization data) back via SSE.

## AI Tools Used

Built using **Gas Town**, a multi-agent orchestration system on **Claude Code**. Gas Town coordinates autonomous worker agents ("polecats") in isolated git worktrees. A spec-first approach was used: the full technical specification ([SPEC.md](SPEC.md)) was written upfront, then work items were dispatched as structured workflow molecules. Each agent implemented, tested, and committed independently — the orchestrator merged results.

## Design Decisions

**pg_duckdb for a single database.** Rather than separate PostgreSQL and DuckDB processes, pg_duckdb combines both. DuckDB's columnar engine handles CSV ingestion and analytics; PostgreSQL handles sessions, conversations, and LangGraph checkpoints. One service, one connection string.

**Direct SSE over LangGraph Platform.** Instead of deploying LangGraph Platform as a separate dependency, the API streams agent events directly through FastAPI using `sse-starlette`. Deployment stays at `docker compose up` with no external services beyond the LLM provider.

**Generative UI.** The agent returns structured `display` metadata (chart type, axes, data) alongside text answers. The frontend renders the appropriate Recharts visualization inline. Clicking a chart expands it into a side panel. The LLM decides the visualization — the frontend just renders it.

**Docker microservices from day one.** All services run in Compose with health checks and dependency ordering. A separate dev compose file adds hot reload. Dev matches production exactly.

## Challenges

Streaming structured data through SSE required careful coordination — tokens stream progressively for responsive UX, but the `message_complete` event carries the full structured response (SQL, display data) for visualization rendering. Getting LangGraph's event stream to emit both token-level and message-level events cleanly took iteration.

pg_duckdb's `read_csv()` creates DuckDB-managed tables inside PostgreSQL. Keeping Alembic migrations unaware of dynamically-created user data tables required explicit exclusion rules in the migration configuration.

## What I'd Improve With More Time

- Multi-table queries — upload multiple CSVs and join across them
- User authentication (OAuth)
- RAG with pgvector for semantic search over data descriptions
- Rich server-side data tables with sorting/filtering/pagination
- Frontend-delegated tool calls — agent requests the browser to act using the user's session
- Export visualizations as PNG/SVG
- Migrate nginx to Traefik for dynamic service routing

## Testing

- **Backend**: pytest + httpx (unit and integration)
- **E2E**: Playwright for upload, chat, and visualization flows
- **CI**: GitHub Actions — lint, type check, tests, E2E on every push
