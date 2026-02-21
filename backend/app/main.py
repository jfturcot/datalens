import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from alembic import command
from app.config import settings
from app.models import engine
from app.routes import conversations, health, sessions, upload

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """Run Alembic migrations to head on startup."""
    alembic_cfg = Config("alembic/alembic.ini")
    alembic_cfg.set_main_option("script_location", "alembic")
    command.upgrade(alembic_cfg, "head")


async def enable_pg_duckdb() -> None:
    """Enable the pg_duckdb extension so read_csv() is available."""
    from sqlalchemy import text

    from app.models.database import async_session_factory

    async with async_session_factory() as session:
        await session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_duckdb"))
        await session.commit()
    logger.info("pg_duckdb extension enabled")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: run migrations, then enable pg_duckdb
    run_migrations()
    logger.info("Database migrations applied")
    await enable_pg_duckdb()

    # Initialize LangGraph checkpoint saver
    async with AsyncPostgresSaver.from_conn_string(
        settings.sync_database_url
    ) as checkpointer:
        await checkpointer.setup()
        logger.info("LangGraph checkpointer initialized")

        # Create agent graph and store on app state
        from app.agent.graph import create_agent_graph

        app.state.agent_graph = create_agent_graph(checkpointer)
        logger.info("Agent graph ready")

        yield
    # Shutdown: dispose engine
    await engine.dispose()


app = FastAPI(title="DataLens API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
