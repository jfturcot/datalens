import uuid
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import get_db
from app.models.session import Session
from app.services.session_service import get_session_by_id


async def get_current_session(
    db: Annotated[AsyncSession, Depends(get_db)],
    datalens_session: Annotated[str | None, Cookie()] = None,
) -> Session:
    """Extract and validate the session from the datalens_session cookie."""
    if datalens_session is None:
        raise HTTPException(status_code=401, detail="Session cookie missing")
    try:
        session_id = uuid.UUID(datalens_session)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid session cookie")
    session = await get_session_by_id(db, session_id)
    if session is None:
        raise HTTPException(status_code=401, detail="Session not found")
    return session
