import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session


async def create_session(db: AsyncSession) -> Session:
    """Create a new session record and return it."""
    session = Session(id=uuid.uuid4())
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session_by_id(db: AsyncSession, session_id: uuid.UUID) -> Session | None:
    """Look up a session by its UUID. Returns None if not found."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    return result.scalar_one_or_none()
