import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.session_service import create_session, get_session_by_id


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    return db


class TestCreateSession:
    async def test_creates_session_and_commits(self, mock_db: AsyncMock) -> None:
        result = await create_session(mock_db)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(result)

    async def test_returns_session_with_uuid(self, mock_db: AsyncMock) -> None:
        await create_session(mock_db)
        added_obj = mock_db.add.call_args[0][0]
        assert isinstance(added_obj.id, uuid.UUID)


class TestGetSessionById:
    async def test_returns_session_when_found(self, mock_db: AsyncMock) -> None:
        session_id = uuid.uuid4()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute.return_value = mock_result

        result = await get_session_by_id(mock_db, session_id)
        assert result is mock_session
        mock_db.execute.assert_awaited_once()

    async def test_returns_none_when_not_found(self, mock_db: AsyncMock) -> None:
        session_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await get_session_by_id(mock_db, session_id)
        assert result is None
