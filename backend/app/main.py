import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alembic import command
from app.models import engine
from app.routes import health, sessions

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """Run Alembic migrations to head on startup."""
    alembic_cfg = Config("alembic/alembic.ini")
    alembic_cfg.set_main_option("script_location", "alembic")
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: run migrations
    run_migrations()
    logger.info("Database migrations applied")
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
