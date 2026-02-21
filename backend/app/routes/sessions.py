from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_session
from app.models import get_db
from app.models.schemas import SessionResponse
from app.models.session import Session
from app.services.session_service import create_session

router = APIRouter()


@router.post("/sessions", response_model=SessionResponse)
async def create_new_session(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JSONResponse:
    """Create a new session and set the session cookie."""
    session = await create_session(db)
    response = JSONResponse(
        content=SessionResponse.model_validate(session).model_dump(mode="json")
    )
    response.set_cookie(
        key="datalens_session",
        value=str(session.id),
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "production",
    )
    return response


@router.get("/sessions/me", response_model=SessionResponse)
async def get_my_session(
    session: Annotated[Session, Depends(get_current_session)],
) -> SessionResponse:
    """Validate the current session cookie and return session info."""
    return SessionResponse.model_validate(session)
