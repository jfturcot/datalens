# DataLens - Technical Specification

## 1. Overview

**DataLens** is a web application that allows users to upload CSV datasets and ask
natural language questions about their data. The application uses an LLM-powered
agent to interpret questions, generate SQL queries, execute them, and return
structured answers with appropriate visualizations.

Built for a take-home assignment for Genesis Computing AI.

## 2. Architecture

### 2.1 Services (Docker Compose)

```
┌─────────────────┐     ┌───────────────────────────────┐
│  frontend        │────▶│  api                          │
│  React SPA       │     │  FastAPI + LangGraph          │
│  Tailwind CSS    │◀────│  ├── REST endpoints           │
│  Recharts        │     │  ├── LangGraph ReAct agent    │
│  nginx :80       │     │  └── Streaming via SSE        │
└─────────────────┘     │         :8000                  │
                         └──────┬──────────┬─────────────┘
                                │          │
                         ┌──────▼───┐  ┌───▼──────────┐
                         │ postgres  │  │ minio        │
                         │ pg_duckdb │  │ S3-compat    │
                         │ :5432     │  │ :9000/:9001  │
                         └──────────┘  └──────────────┘
```

| Service    | Image                           | Purpose                                           |
|------------|---------------------------------|---------------------------------------------------|
| frontend   | Custom (node build + nginx)     | Serves React SPA + reverse proxy for /api/*       |
| api        | Custom (python:3.12-slim)       | FastAPI app with LangGraph agent                  |
| postgres   | pgduckdb/pgduckdb:18-v1.1.1    | Analytical queries (DuckDB) + checkpoints (PG)    |
| minio      | minio/minio                     | S3-compatible storage for uploaded CSV files       |

### 2.2 Why These Choices

- **pg_duckdb**: Single database for both analytical SQL (DuckDB engine) and
  application state (native PostgreSQL). DuckDB provides `read_csv()`, columnar
  query execution, and automatic type inference. PostgreSQL handles LangGraph
  checkpoints and session storage. One service instead of two.

- **MinIO**: S3-compatible object storage. Stores raw uploaded CSV files. More
  production-realistic than Docker volumes for file storage. Enables future
  migration to real S3.

- **LangGraph**: Provides the agent orchestration loop, tool calling, streaming,
  and conversation memory via checkpoints.

- **FastAPI**: Async Python framework. Native support for SSE streaming, Pydantic
  validation, and clean REST API design. LangGraph integrates naturally.

- **React + Tailwind + Recharts**: Standard frontend stack. Recharts is the most
  widely-used React charting library. Tailwind enables dark/light mode with
  minimal CSS.

## 3. User Flow

### 3.1 Initial State

1. User opens the app.
2. A session cookie is set (UUID). This persists across page refreshes.
3. The main view is a full-page chat interface.
4. The chat input is **disabled**. A file drop zone is displayed in the chat area
   with the message: "Drop a CSV file here to get started, or click to browse."
5. If the user types before uploading, the agent responds:
   "I need data before I can help. Please upload a CSV file to get started."

### 3.2 File Upload

1. User drops or selects a CSV file.
2. Frontend shows upload progress.
3. File is sent to `POST /api/upload`.
4. Backend validates:
   - Must be a `.csv` file (check extension and content-type).
   - Maximum file size: 10MB.
   - Must be valid CSV (parseable, non-empty, has headers).
5. Backend stores the raw file in MinIO under
   `uploads/{session_id}/{filename}`.
6. Backend loads the CSV into PostgreSQL via pg_duckdb:
   - Table name derived from filename (sanitized, e.g., `sample_data`).
   - DuckDB's `read_csv()` auto-detects column types.
7. Backend creates a new conversation record and LangGraph thread.
8. The chat input is **enabled**.
9. The agent sends a greeting message:
   "I've loaded **sample_data.csv** — 500 rows, 7 columns:
   `company_name` (text), `industry_vertical` (text), `founding_year` (integer),
   `arr_thousands` (integer), `employee_count` (integer),
   `churn_rate_percent` (float), `yoy_growth_rate_percent` (float).
   What would you like to know?"

### 3.3 Conversation

1. User types a question in natural language.
2. Frontend sends the message via `POST /api/conversations/{id}/messages`.
3. Response streams back via SSE (Server-Sent Events).
4. The LangGraph agent:
   a. Calls `inspect_schema` tool to get table/column metadata.
   b. Generates a SQL query based on the user's question and schema.
   c. Calls `execute_query` tool with the generated SQL.
   d. If the query fails, the agent sees the error and retries (up to 3 attempts).
   e. Formats the answer as structured JSON with display hints.
5. Frontend renders the response:
   - Text answer is always shown.
   - SQL query is shown in a collapsible block (collapsed by default).
   - If visualization data is present, a chart/table is rendered inline.
   - Visualization bubbles are clickable to expand into a side panel.

### 3.4 Multiple Conversations

- A left sidebar shows conversation tabs, similar to Claude's web UI.
- Each tab is labeled with the uploaded filename.
- Users can create new conversations (which requires a new file upload).
- Users can switch between conversations.
- Users can delete conversations.
- Conversation state persists across page refreshes (via session cookie +
  PostgreSQL checkpoints).

## 4. API Design

### 4.1 Endpoints

| Method | Path                                  | Purpose                       |
|--------|---------------------------------------|-------------------------------|
| GET    | /api/health                           | Health check                  |
| POST   | /api/sessions                         | Create session (sets cookie)  |
| GET    | /api/sessions/me                      | Validate current session      |
| POST   | /api/upload                           | Upload a CSV file             |
| GET    | /api/conversations                    | List conversations for session|
| POST   | /api/conversations                    | Create new conversation       |
| GET    | /api/conversations/{id}               | Get conversation history      |
| DELETE | /api/conversations/{id}               | Delete a conversation         |
| POST   | /api/conversations/{id}/messages      | Send message (SSE streaming)  |

### 4.2 Upload Endpoint

```
POST /api/upload
Content-Type: multipart/form-data

Request:
  file: <CSV file, max 10MB>

Response 200:
{
  "conversation_id": "uuid",
  "filename": "sample_data.csv",
  "table_name": "sample_data",
  "row_count": 500,
  "columns": [
    {"name": "company_name", "type": "text"},
    {"name": "arr_thousands", "type": "integer"},
    ...
  ]
}

Response 400:
{"error": "File must be a CSV", "detail": "..."}

Response 413:
{"error": "File too large", "detail": "Maximum file size is 10MB"}
```

### 4.3 Message Endpoint (Streaming)

```
POST /api/conversations/{id}/messages
Content-Type: application/json

Request:
{
  "content": "What's the average ARR for fintech companies?"
}

Response: text/event-stream (SSE)

event: token
data: {"content": "The"}

event: token
data: {"content": " average"}

...

event: message_complete
data: {
  "content": "The average ARR for fintech companies is $1,245K.",
  "sql": "SELECT AVG(arr_thousands) FROM sample_data WHERE industry_vertical = 'Fintech'",
  "display": {
    "type": "bar_chart",
    "title": "Average ARR by Industry",
    "data": [
      {"industry_vertical": "Fintech", "avg_arr": 1245.3},
      ...
    ],
    "x_axis": "industry_vertical",
    "y_axis": "avg_arr"
  }
}
```

### 4.4 Reverse Proxy (nginx)

The frontend nginx container serves dual purpose: static SPA files and reverse
proxy for the API. All traffic enters on port 80.

```nginx
server {
    listen 80;

    # API requests → FastAPI backend
    location /api/ {
        proxy_pass http://api:8000;
        proxy_http_version 1.1;
        proxy_set_header Connection "";          # SSE: disable buffering
        proxy_buffering off;                      # SSE: stream immediately
        proxy_cache off;                          # SSE: no caching
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;                  # Long timeout for SSE streams
    }

    # Everything else → React SPA
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;         # SPA client-side routing
    }
}
```

### 4.5 Session Management

- On first load, the React app checks for a `datalens_session` cookie.
- If no cookie exists, the app calls `POST /api/sessions` to create one.
- FastAPI creates a session record in PostgreSQL and returns
  `Set-Cookie: datalens_session=<uuid>` (HttpOnly, SameSite=Lax, Secure in prod).
- If the cookie exists (page refresh), the app calls `GET /api/sessions/me` to
  validate the session is still active, then loads the conversation list.
- All conversation and upload endpoints are scoped to the session cookie.
- No authentication required. Auth is on the roadmap.

## 5. LangGraph Agent

### 5.1 Agent Type

ReAct agent using LangGraph's `create_react_agent` or equivalent graph
construction. The agent has access to tools and decides when to call them.

### 5.2 Model

- Model: `claude-sonnet-4-5` via LiteLLM proxy.
- Base URL: Configured via `LITELLM_API_URL` environment variable.
- API Key: Configured via `LITELLM_API_KEY` environment variable.
- Uses the OpenAI-compatible API format (LiteLLM provides this).

### 5.3 Tools

#### inspect_schema

```python
def inspect_schema(table_name: str) -> dict:
    """
    Returns the schema of a table in the database.

    Returns:
    {
        "table_name": "sample_data",
        "row_count": 500,
        "columns": [
            {"name": "company_name", "type": "text", "sample_values": ["SignalTech", "VertexSync", "TerraBase"]},
            {"name": "arr_thousands", "type": "integer", "min": 100, "max": 9800, "mean": 2450.5},
            ...
        ]
    }

    For text columns: includes sample_values (up to 5 unique values).
    For numeric columns: includes min, max, mean.
    """
```

#### execute_query

```python
def execute_query(sql: str) -> dict:
    """
    Executes a read-only SQL query against the database.
    Returns results as a list of dictionaries.

    The query MUST be a SELECT statement. No INSERT, UPDATE, DELETE, DROP, or DDL.
    Maximum 500 rows returned. Queries timeout after 10 seconds.

    Returns:
    {
        "success": true,
        "row_count": 42,
        "columns": ["company_name", "arr_thousands"],
        "rows": [
            {"company_name": "SignalTech", "arr_thousands": 816},
            ...
        ]
    }

    On error:
    {
        "success": false,
        "error": "Column 'revenue' does not exist. Available columns: arr_thousands, ..."
    }
    """
```

### 5.4 System Prompt

The agent receives a system prompt that includes:
- Its role: "You are a data analyst assistant."
- Instructions to always call `inspect_schema` before generating SQL.
- Instructions to generate PostgreSQL-compatible SQL (DuckDB engine).
- Instructions to retry on SQL errors (up to 3 attempts) before telling the user.
- Instructions for structured output: always include a `display` object in the
  final response indicating how to visualize the results.
- Display type selection guidance:
  - Single value → `text`
  - Comparison across categories → `bar_chart`
  - Trend over time → `line_chart`
  - Distribution / proportion → `pie_chart`
  - Correlation between two numeric fields → `scatter_plot`
  - List of records → `table`

### 5.5 Checkpointing

- Uses `langgraph-checkpoint-postgres` v3.x with `AsyncPostgresSaver`.
- Initialized via FastAPI's `lifespan` context manager.
- Each conversation has a unique `thread_id` mapped to the conversation UUID.
- Checkpoints persist across server restarts.

### 5.6 Streaming

- LangGraph's `astream_events` is used to stream tokens and tool call events.
- FastAPI wraps this in an SSE response using `sse-starlette`'s
  `EventSourceResponse`.
- The frontend consumes the SSE stream using `@microsoft/fetch-event-source`
  (supports POST requests, unlike native `EventSource` which is GET-only).
- A custom `useChat` React hook wraps `fetch-event-source`, manages message
  state, and exposes `submit()`, `stop()`, and `isLoading` to components.
- SSE event types sent by the backend:
  - `event: token` — individual LLM token chunk for progressive text rendering.
  - `event: tool_start` — agent is calling a tool (includes tool name, e.g.,
    "inspect_schema", "execute_query"). Frontend shows status indicator.
  - `event: tool_end` — tool call completed (includes result summary).
  - `event: message_complete` — final structured response with `content`, `sql`,
    and `display` fields. Frontend renders the full message with visualization.
  - `event: error` — agent error (includes error message for display).

## 6. Generative UI

### 6.1 Display Types

The agent's final response includes a `display` object that the frontend uses
to render the appropriate visualization.

| Type          | When Used                              | React Component       |
|---------------|----------------------------------------|-----------------------|
| `text`        | Single value answers                   | TextAnswer            |
| `table`       | List of records                        | DataTable             |
| `bar_chart`   | Comparison across categories           | BarChartViz           |
| `line_chart`  | Trends over time                       | LineChartViz          |
| `pie_chart`   | Distribution / proportions             | PieChartViz           |
| `scatter_plot` | Correlation between numeric fields    | ScatterPlotViz        |

### 6.2 Display Schema

```typescript
interface DisplayData {
  type: "text" | "table" | "bar_chart" | "line_chart" | "pie_chart" | "scatter_plot";
  title?: string;
  data: Record<string, any>[];
  x_axis?: string;     // field name for x-axis (charts)
  y_axis?: string;     // field name for y-axis (charts)
  label_key?: string;  // field name for labels (pie chart)
  value_key?: string;  // field name for values (pie chart)
}
```

### 6.3 Expandable Visualization

- Chart/table visualizations render inline in the chat bubble at a compact size.
- Clicking a visualization opens a side panel (right side of the screen) with a
  larger representation.
- The chat area shrinks to accommodate the panel (responsive layout).
- The panel can be closed to return to full-width chat.

## 7. Frontend

### 7.1 Tech Stack

- React 19 (with Vite as build tool)
- TypeScript
- Tailwind CSS v4
- Recharts for visualizations
- `@microsoft/fetch-event-source` for SSE streaming (POST support)

### 7.2 Component Structure

```
src/
├── components/
│   ├── chat/
│   │   ├── ChatWindow.tsx        # Main chat container
│   │   ├── MessageBubble.tsx     # Individual message (user or agent)
│   │   ├── ChatInput.tsx         # Text input + send button
│   │   ├── FileDropZone.tsx      # CSV upload drop area
│   │   ├── SQLBlock.tsx          # Collapsible SQL display
│   │   └── StatusIndicator.tsx   # "Inspecting schema..." / "Running query..."
│   ├── viz/
│   │   ├── VizPanel.tsx          # Expandable side panel for visualizations
│   │   ├── BarChartViz.tsx       # Bar chart component (Recharts)
│   │   ├── LineChartViz.tsx      # Line chart component
│   │   ├── PieChartViz.tsx       # Pie chart component
│   │   ├── ScatterPlotViz.tsx    # Scatter plot component
│   │   ├── DataTable.tsx         # Simple rendered table
│   │   └── TextAnswer.tsx        # Single-value text display
│   └── layout/
│       ├── Sidebar.tsx           # Conversation tabs
│       ├── Header.tsx            # App header with theme toggle
│       └── Layout.tsx            # Main layout wrapper
├── hooks/
│   ├── useChat.ts                # Custom SSE streaming hook (fetch-event-source)
│   ├── useFileUpload.ts          # File upload logic
│   └── useConversations.ts       # Conversation CRUD
├── lib/
│   ├── api.ts                    # API client
│   └── types.ts                  # Shared TypeScript types
├── App.tsx
└── main.tsx
```

### 7.3 UI States

| State                | Chat Input | Drop Zone | Agent Behavior                    |
|----------------------|------------|-----------|-----------------------------------|
| No file uploaded     | Disabled   | Visible   | Prompts for file upload           |
| Uploading            | Disabled   | Progress  | N/A                               |
| File loaded          | Enabled    | Hidden    | Greets with schema summary        |
| Waiting for response | Disabled   | Hidden    | Streaming tokens                  |
| Response complete    | Enabled    | Hidden    | Idle                              |
| Error                | Enabled    | Hidden    | Shows error, user can retry       |

### 7.4 Dark/Light Mode

- Toggle in the header.
- Uses Tailwind's `dark:` variant.
- Preference saved to localStorage.
- Defaults to system preference via `prefers-color-scheme`.

## 8. Backend

### 8.1 Project Structure

```
backend/
├── alembic/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI app, lifespan, middleware
│   ├── config.py                 # Settings from environment variables
│   ├── dependencies.py           # FastAPI dependencies (db session, etc.)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py             # GET /api/health
│   │   ├── upload.py             # POST /api/upload
│   │   └── conversations.py      # Conversation + message endpoints
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py              # LangGraph agent definition
│   │   ├── tools.py              # inspect_schema, execute_query
│   │   ├── prompts.py            # System prompt
│   │   └── streaming.py          # SSE streaming utilities
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py           # SQLAlchemy / asyncpg setup
│   │   └── schemas.py            # Pydantic models for API
│   └── services/
│       ├── __init__.py
│       ├── csv_service.py        # CSV validation, DuckDB ingestion
│       ├── storage_service.py    # MinIO operations
│       └── session_service.py    # Session/cookie management
├── tests/
│   ├── conftest.py               # Fixtures (test db, test client, etc.)
│   ├── unit/
│   │   ├── test_csv_service.py
│   │   ├── test_tools.py
│   │   └── test_schemas.py
│   └── integration/
│       ├── test_upload.py
│       ├── test_conversations.py
│       └── test_agent.py
├── Dockerfile
├── pyproject.toml
└── uv.lock
```

### 8.2 Key Dependencies

```
fastapi
uvicorn[standard]
sse-starlette              # SSE responses for streaming
langgraph>=0.4
langchain-openai           # For ChatOpenAI (LiteLLM-compatible)
langgraph-checkpoint-postgres>=3.0
psycopg[binary,pool]       # Async PostgreSQL driver
sqlalchemy[asyncio]        # ORM for session/conversation tables
alembic                    # Database migrations
asyncpg                    # Async PG driver for SQLAlchemy
duckdb                     # For direct DuckDB operations if needed
miniopy-async              # Async MinIO client
python-multipart           # For file uploads
pydantic>=2.0
pydantic-settings          # For config from env vars
pytest
pytest-asyncio
httpx                      # For test client
```

### 8.3 Database Schema & Migrations

Uses SQLAlchemy ORM models with **Alembic** for migrations. Migrations run
automatically on application startup (via the FastAPI lifespan handler) or
manually with `alembic upgrade head`.

```
backend/
├── alembic/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/           # Migration files (auto-generated)
```

**ORM Models** (in `app/models/`):

```python
# app/models/session.py
class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, server_default=func.now()
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

# app/models/conversation.py
class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE")
    )
    filename: Mapped[str]
    table_name: Mapped[str]
    row_count: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, server_default=func.now()
    )
    session: Mapped["Session"] = relationship(back_populates="conversations")
```

**Notes:**
- LangGraph checkpoint tables are auto-created by `AsyncPostgresSaver.setup()`
  (not managed by Alembic — LangGraph owns its schema).
- User-uploaded data tables are created dynamically by the CSV ingestion service
  via pg_duckdb's `CREATE TABLE ... AS SELECT * FROM read_csv(...)`.
- Alembic's `env.py` is configured to exclude both LangGraph tables and
  dynamically-created data tables from auto-generation.

### 8.4 CSV Ingestion

When a CSV is uploaded:

```sql
-- 1. Create table from CSV using pg_duckdb's read_csv
CREATE TABLE {table_name} AS
SELECT * FROM read_csv('/path/to/temp/file.csv');

-- 2. Verify row count
SELECT COUNT(*) FROM {table_name};
```

Table naming:
- Derived from filename: `sample_data.csv` → `sample_data`
- Sanitized: lowercase, alphanumeric + underscores only.
- Prefixed with session ID fragment to avoid collisions:
  `s_{session_id_first8}_{sanitized_filename}`

### 8.5 Query Safety

- The `execute_query` tool only accepts SELECT statements.
- SQL is validated before execution: reject any DDL or DML keywords
  (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE).
- Queries have a 10-second timeout.
- Results are limited to 500 rows.
- The DuckDB execution runs in a read-only context where possible.

## 9. Environment Configuration

### 9.1 .env.example

```env
# LLM Configuration
LITELLM_API_URL=https://litellm-production-f079.up.railway.app/
LITELLM_API_KEY=your-api-key-here
LITELLM_MODEL=claude-sonnet-4-5

# PostgreSQL (pg_duckdb)
POSTGRES_USER=datalens
POSTGRES_PASSWORD=change-me-in-production
POSTGRES_DB=datalens
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# MinIO
MINIO_ROOT_USER=datalens
MINIO_ROOT_PASSWORD=change-me-in-production
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET=uploads
MINIO_USE_SSL=false

# App
APP_ENV=development
SESSION_SECRET=change-me-in-production
```

### 9.2 Docker Compose

```yaml
version: "3.8"

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - api

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    expose:
      - "8000"                  # Internal only — nginx proxies /api/*
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      minio:
        condition: service_started

  postgres:
    image: pgduckdb/pgduckdb:18-v1.1.1
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - miniodata:/data
    ports:
      - "9000:9000"
      - "9001:9001"

volumes:
  pgdata:
  miniodata:
```

## 10. Project Root Structure

```
datalens/
├── frontend/
│   ├── src/                    # React source (see section 7.2)
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── Dockerfile
│   └── nginx.conf
├── backend/
│   ├── app/                    # Python source (see section 8.1)
│   ├── tests/
│   ├── pyproject.toml
│   ├── uv.lock
│   └── Dockerfile
├── e2e/
│   ├── tests/
│   │   ├── upload.spec.ts
│   │   ├── chat.spec.ts
│   │   └── visualization.spec.ts
│   ├── playwright.config.ts
│   └── package.json
├── docker-compose.yml
├── docker-compose.test.yml     # Test configuration with test databases
├── .env.example
├── .gitignore
├── .github/
│   └── workflows/
│       ├── ci.yml              # Lint + test on push
│       └── deploy.yml          # Deploy on merge to main
├── CLAUDE.md                   # Project standards for AI agents
└── README.md                   # Submission README (max 500 words)
```

## 11. Testing Strategy

### 11.1 Backend Unit Tests (pytest)

- **test_csv_service.py**: CSV validation (valid CSV, empty file, too large,
  non-CSV, malformed headers). Table name sanitization.
- **test_tools.py**: inspect_schema returns correct structure. execute_query
  rejects non-SELECT statements. execute_query handles SQL errors gracefully.
  Row limit enforcement. Timeout enforcement.
- **test_schemas.py**: Pydantic model validation for all request/response schemas.

### 11.2 Backend Integration Tests (pytest + httpx)

- **test_upload.py**: Full upload flow — file → MinIO → DuckDB table → response.
  Invalid file rejection. File size limit enforcement.
- **test_conversations.py**: CRUD operations on conversations. Session scoping
  (can't access another session's conversations). Conversation deletion cascades.
- **test_agent.py**: Agent generates valid SQL for known questions. Agent retries
  on SQL errors. Agent returns structured display data. Streaming responses
  contain expected SSE events.

### 11.3 E2E Tests (Playwright)

- **upload.spec.ts**: Drop CSV file → see schema greeting. Reject non-CSV file.
  Reject oversized file.
- **chat.spec.ts**: Ask "What's the average ARR for fintech companies?" → get
  a numeric answer. Ask "Which company has the highest growth rate?" → get a
  company name. Ask a malformed question → get a graceful error message.
- **visualization.spec.ts**: Ask a question that triggers a bar chart → chart
  renders. Click chart → side panel opens. Close panel → returns to full chat.

### 11.4 Test Infrastructure

- `docker-compose.test.yml` spins up test postgres and minio instances.
- Backend tests use a test database that is reset between test modules.
- E2E tests run against the full Docker Compose stack.
- CI runs: backend lint → backend unit tests → backend integration tests →
  build frontend → E2E tests.

## 12. CI/CD

### 12.1 CI Pipeline (GitHub Actions — ci.yml)

Triggers: push to any branch, pull requests to main.

```
Jobs:
  backend-lint:
    - ruff check
    - ruff format --check
    - mypy (type checking)

  backend-test:
    - Start postgres (pg_duckdb) and minio services
    - Run pytest (unit + integration)
    - Upload coverage report

  frontend-lint:
    - eslint
    - tsc --noEmit (type checking)

  frontend-build:
    - npm run build (verify it compiles)

  e2e:
    - docker compose -f docker-compose.test.yml up
    - Run playwright tests
    - Upload test artifacts (screenshots on failure)
```

### 12.2 Deploy Pipeline (GitHub Actions — deploy.yml)

Triggers: merge to main.

```
Jobs:
  deploy:
    - SSH into Digital Ocean droplet
    - git pull
    - docker compose build
    - docker compose up -d
    - Health check: curl /api/health
```

## 13. Deployment

- **Host**: Digital Ocean droplet (8GB RAM).
- **Domain**: TBD (purchased for submission, Cloudflare DNS + SSL).
- **SSL**: Cloudflare handles TLS termination.
- **Process**: Docker Compose runs all 4 services on the droplet.
- **Updates**: Push to main triggers GitHub Actions deploy.

## 14. Roadmap (Not Built — Mentioned in README)

- User authentication (OAuth / email+password)
- Virus scanner on file uploads (ClamAV integration)
- Multi-table / cross-table queries (upload multiple CSVs, join across them)
- Rich data tables with sorting, filtering, and pagination (server-side)
- Auto-generated conversation titles via LLM summarization
- RAG with pgvector (same PostgreSQL instance — pg_duckdb + pgvector compatible)
- Additional data source support (Excel, JSON, Parquet)
- Frontend-delegated tool calls — the agent can request the frontend to execute
  tools (e.g., API calls, GraphQL mutations) using the current user's session.
  The backend sends a `tool_request` SSE event, the frontend executes with the
  user's auth context, and returns the result. This enables the agent to act on
  behalf of the user without the backend ever handling user credentials —
  effectively "replacing the mouse clicks."
- Migrate from nginx to Traefik for reverse proxy (needed when adding more
  microservices — auto-discovery, dynamic routing, built-in SSL)
- Export visualizations as PNG/SVG
- Share conversation via link

## 15. CLAUDE.md (Project Standards)

This file will live at the repo root and govern all AI agent behavior:

```markdown
# DataLens

## Tech Stack
- Backend: Python 3.12, FastAPI, LangGraph, SQLAlchemy
- Frontend: React 19, TypeScript, Vite, Tailwind CSS v4, Recharts
- Database: PostgreSQL 18 with pg_duckdb extension
- Storage: MinIO (S3-compatible)
- Package management: uv (backend), npm (frontend)

## Code Standards
- Backend: Format with ruff. Type hints on all function signatures.
- Frontend: ESLint + Prettier. Strict TypeScript (no `any`).
- All API endpoints must have Pydantic request/response models.
- All components must be typed with TypeScript interfaces.

## Testing Requirements
- Every backend endpoint must have integration tests.
- Every service function must have unit tests.
- Every user-facing feature must have an E2E test.
- Tests must pass before merging to main.
- Use pytest + httpx for backend, Playwright for E2E.

## Git Workflow
- Feature branches off main.
- Conventional commits (feat:, fix:, test:, docs:, refactor:).
- PRs require CI green before merge.

## Architecture Rules
- SQL queries generated by the agent MUST be read-only (SELECT only).
- All user input must be validated at the API boundary.
- File uploads must be validated (type, size, content).
- Environment secrets must NEVER be committed. Use .env.
- All async code must use async/await (no sync blocking in async context).
```
