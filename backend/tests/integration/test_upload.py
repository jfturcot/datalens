import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


def _session_cookie(session_id: str) -> dict[str, str]:
    return {"datalens_session": session_id}


@pytest.fixture
async def session_id(client: AsyncClient) -> str:
    """Create a session and return its id."""
    resp = await client.post("/api/sessions")
    assert resp.status_code == 200
    return resp.json()["id"]


def _csv_bytes(
    header: str = "name,age",
    rows: list[str] | None = None,
) -> bytes:
    if rows is None:
        rows = ["Alice,30", "Bob,25"]
    return (header + "\n" + "\n".join(rows) + "\n").encode()


def _patch_minio():
    """Patch the MinIO upload so it does nothing."""
    return patch(
        "app.routes.upload.upload_file",
        new_callable=AsyncMock,
        return_value="fake/path.csv",
    )


class _FakeResult:
    """Stub for SQLAlchemy result objects returned by mocked execute."""

    def __init__(self, scalar_val, rows=None):
        self._scalar = scalar_val
        self._rows = rows or []

    def scalar(self):
        return self._scalar

    def fetchall(self):
        return self._rows


FAKE_COLUMNS = [("name", "text"), ("age", "integer")]


class TestUploadEndpoint:
    @pytest.mark.anyio
    async def test_successful_upload(
        self,
        client: AsyncClient,
        session_id: str,
    ) -> None:
        from app.models.database import get_db

        orig_override = client._transport.app.dependency_overrides.get(get_db)  # type: ignore[attr-defined]

        async def patched_get_db():
            async for db in orig_override():
                real_exec = db.execute

                async def _exec(stmt, params=None, **kw):
                    sql = str(stmt)
                    if "read_csv" in sql:
                        return _FakeResult(None)
                    if "SELECT COUNT(*)" in sql:
                        return _FakeResult(2)
                    if "information_schema" in sql:
                        return _FakeResult(None, FAKE_COLUMNS)
                    return await real_exec(stmt, params, **kw)

                db.execute = _exec  # type: ignore[assignment]
                yield db

        app = client._transport.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_db] = patched_get_db

        with (
            _patch_minio(),
            patch("app.routes.upload.os.makedirs"),
            patch("builtins.open", create=True),
            patch(
                "app.routes.upload.os.path.exists",
                return_value=True,
            ),
            patch("app.routes.upload.os.unlink"),
        ):
            resp = await client.post(
                "/api/upload",
                files={
                    "file": (
                        "test.csv",
                        _csv_bytes(),
                        "text/csv",
                    )
                },
                cookies=_session_cookie(session_id),
            )

        if orig_override:
            app.dependency_overrides[get_db] = orig_override

        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "test.csv"
        assert data["row_count"] == 2
        assert data["table_name"].startswith("s_")
        assert len(data["columns"]) == 2
        assert data["columns"][0]["name"] == "name"
        assert "conversation_id" in data
        uuid.UUID(data["conversation_id"])

    @pytest.mark.anyio
    async def test_reject_non_csv_extension(
        self,
        client: AsyncClient,
        session_id: str,
    ) -> None:
        resp = await client.post(
            "/api/upload",
            files={
                "file": (
                    "data.xlsx",
                    b"content",
                    "application/octet-stream",
                )
            },
            cookies=_session_cookie(session_id),
        )
        assert resp.status_code == 400
        assert "CSV" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_reject_wrong_content_type(
        self,
        client: AsyncClient,
        session_id: str,
    ) -> None:
        resp = await client.post(
            "/api/upload",
            files={
                "file": (
                    "data.csv",
                    b"name,age\nA,1\n",
                    "application/json",
                )
            },
            cookies=_session_cookie(session_id),
        )
        assert resp.status_code == 400
        assert "CSV" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_reject_empty_file(
        self,
        client: AsyncClient,
        session_id: str,
    ) -> None:
        resp = await client.post(
            "/api/upload",
            files={"file": ("empty.csv", b"", "text/csv")},
            cookies=_session_cookie(session_id),
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_reject_headers_only(
        self,
        client: AsyncClient,
        session_id: str,
    ) -> None:
        resp = await client.post(
            "/api/upload",
            files={
                "file": (
                    "headers.csv",
                    b"name,age\n",
                    "text/csv",
                )
            },
            cookies=_session_cookie(session_id),
        )
        assert resp.status_code == 400
        assert "data rows" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_reject_oversized_file(
        self,
        client: AsyncClient,
        session_id: str,
    ) -> None:
        big = b"x" * (10 * 1024 * 1024 + 1)
        resp = await client.post(
            "/api/upload",
            files={"file": ("big.csv", big, "text/csv")},
            cookies=_session_cookie(session_id),
        )
        assert resp.status_code == 413

    @pytest.mark.anyio
    async def test_reject_no_session(
        self,
        client: AsyncClient,
    ) -> None:
        resp = await client.post(
            "/api/upload",
            files={
                "file": (
                    "test.csv",
                    _csv_bytes(),
                    "text/csv",
                )
            },
        )
        assert resp.status_code == 401
