import uuid
from datetime import UTC, datetime

from app.models.schemas import HealthResponse, SessionResponse


class TestSessionResponse:
    def test_from_dict(self) -> None:
        now = datetime.now(UTC)
        uid = uuid.uuid4()
        resp = SessionResponse(id=uid, created_at=now)
        assert resp.id == uid
        assert resp.created_at == now

    def test_json_serialization(self) -> None:
        now = datetime.now(UTC)
        uid = uuid.uuid4()
        resp = SessionResponse(id=uid, created_at=now)
        data = resp.model_dump(mode="json")
        assert data["id"] == str(uid)
        assert isinstance(data["created_at"], str)


class TestHealthResponse:
    def test_ok(self) -> None:
        resp = HealthResponse(status="ok")
        assert resp.status == "ok"
