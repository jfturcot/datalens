import uuid

from httpx import AsyncClient


class TestCreateSession:
    async def test_creates_session_returns_200(self, client: AsyncClient) -> None:
        response = await client.post("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "created_at" in data
        # Verify it's a valid UUID
        uuid.UUID(data["id"])

    async def test_sets_session_cookie(self, client: AsyncClient) -> None:
        response = await client.post("/api/sessions")
        assert response.status_code == 200
        cookies = response.cookies
        assert "datalens_session" in cookies
        session_id = cookies["datalens_session"]
        # Cookie value should match the returned session ID
        assert session_id == response.json()["id"]

    async def test_multiple_sessions_are_unique(self, client: AsyncClient) -> None:
        r1 = await client.post("/api/sessions")
        r2 = await client.post("/api/sessions")
        assert r1.json()["id"] != r2.json()["id"]


class TestGetMySession:
    async def test_returns_session_with_valid_cookie(self, client: AsyncClient) -> None:
        # Create a session first
        create_resp = await client.post("/api/sessions")
        session_id = create_resp.json()["id"]

        # Validate it
        response = await client.get(
            "/api/sessions/me", cookies={"datalens_session": session_id}
        )
        assert response.status_code == 200
        assert response.json()["id"] == session_id

    async def test_returns_401_without_cookie(self, client: AsyncClient) -> None:
        response = await client.get("/api/sessions/me")
        assert response.status_code == 401

    async def test_returns_401_with_invalid_uuid(self, client: AsyncClient) -> None:
        response = await client.get(
            "/api/sessions/me", cookies={"datalens_session": "not-a-uuid"}
        )
        assert response.status_code == 401

    async def test_returns_401_with_nonexistent_session(
        self, client: AsyncClient
    ) -> None:
        fake_id = str(uuid.uuid4())
        response = await client.get(
            "/api/sessions/me", cookies={"datalens_session": fake_id}
        )
        assert response.status_code == 401


class TestHealthEndpoint:
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        response = await client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
