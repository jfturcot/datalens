import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation


def _session_cookie(session_id: str) -> dict[str, str]:
    return {"datalens_session": session_id}


@pytest.fixture
async def session_id(client: AsyncClient) -> str:
    """Create a session and return its id."""
    resp = await client.post("/api/sessions")
    assert resp.status_code == 200
    return resp.json()["id"]


@pytest.fixture
async def conversation_id(
    client: AsyncClient, session_id: str, test_session: AsyncSession
) -> str:
    """Create a conversation record in the test database."""
    conv = Conversation(
        id=uuid.uuid4(),
        session_id=uuid.UUID(session_id),
        filename="test.csv",
        table_name="s_test_table",
        row_count=10,
    )
    test_session.add(conv)
    await test_session.commit()
    return str(conv.id)


class TestListConversations:
    async def test_returns_empty_list_initially(
        self, client: AsyncClient, session_id: str
    ) -> None:
        resp = await client.get(
            "/api/conversations",
            cookies=_session_cookie(session_id),
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_conversations_for_session(
        self, client: AsyncClient, session_id: str, conversation_id: str
    ) -> None:
        resp = await client.get(
            "/api/conversations",
            cookies=_session_cookie(session_id),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == conversation_id
        assert data[0]["filename"] == "test.csv"
        assert data[0]["table_name"] == "s_test_table"
        assert data[0]["row_count"] == 10

    async def test_does_not_return_other_sessions_conversations(
        self, client: AsyncClient, session_id: str, conversation_id: str
    ) -> None:
        # Create another session
        resp2 = await client.post("/api/sessions")
        other_session_id = resp2.json()["id"]

        resp = await client.get(
            "/api/conversations",
            cookies=_session_cookie(other_session_id),
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_requires_session(self, client: AsyncClient) -> None:
        resp = await client.get("/api/conversations")
        assert resp.status_code == 401


class TestGetConversation:
    async def test_returns_conversation_detail(
        self, client: AsyncClient, session_id: str, conversation_id: str
    ) -> None:
        # Mock the agent graph state retrieval
        mock_graph = MagicMock()
        mock_state = MagicMock()
        mock_state.values = {"messages": []}
        mock_graph.aget_state = AsyncMock(return_value=mock_state)

        app = client._transport.app  # type: ignore[attr-defined]
        app.state.agent_graph = mock_graph

        resp = await client.get(
            f"/api/conversations/{conversation_id}",
            cookies=_session_cookie(session_id),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == conversation_id
        assert data["filename"] == "test.csv"
        assert data["messages"] == []

    async def test_returns_message_history(
        self, client: AsyncClient, session_id: str, conversation_id: str
    ) -> None:
        # Create mock messages
        human_msg = MagicMock()
        human_msg.type = "human"
        human_msg.content = "What is the average age?"

        ai_msg = MagicMock()
        ai_msg.type = "ai"
        ai_msg.content = "The average age is 30."

        mock_graph = MagicMock()
        mock_state = MagicMock()
        mock_state.values = {"messages": [human_msg, ai_msg]}
        mock_graph.aget_state = AsyncMock(return_value=mock_state)

        app = client._transport.app  # type: ignore[attr-defined]
        app.state.agent_graph = mock_graph

        resp = await client.get(
            f"/api/conversations/{conversation_id}",
            cookies=_session_cookie(session_id),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][0]["content"] == "What is the average age?"
        assert data["messages"][1]["role"] == "assistant"
        assert data["messages"][1]["content"] == "The average age is 30."

    async def test_returns_404_for_nonexistent_conversation(
        self, client: AsyncClient, session_id: str
    ) -> None:
        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/api/conversations/{fake_id}",
            cookies=_session_cookie(session_id),
        )
        assert resp.status_code == 404

    async def test_returns_404_for_other_sessions_conversation(
        self, client: AsyncClient, session_id: str, conversation_id: str
    ) -> None:
        # Create another session
        resp2 = await client.post("/api/sessions")
        other_session_id = resp2.json()["id"]

        resp = await client.get(
            f"/api/conversations/{conversation_id}",
            cookies=_session_cookie(other_session_id),
        )
        assert resp.status_code == 404

    async def test_requires_session(self, client: AsyncClient) -> None:
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/conversations/{fake_id}")
        assert resp.status_code == 401


class TestDeleteConversation:
    async def test_deletes_conversation(
        self, client: AsyncClient, session_id: str, conversation_id: str
    ) -> None:
        # Verify conversation exists first
        resp = await client.get(
            "/api/conversations",
            cookies=_session_cookie(session_id),
        )
        assert len(resp.json()) == 1

        resp = await client.delete(
            f"/api/conversations/{conversation_id}",
            cookies=_session_cookie(session_id),
        )
        assert resp.status_code == 204

        # Verify conversation is gone
        resp = await client.get(
            "/api/conversations",
            cookies=_session_cookie(session_id),
        )
        assert resp.json() == []

    async def test_returns_404_for_nonexistent(
        self, client: AsyncClient, session_id: str
    ) -> None:
        fake_id = str(uuid.uuid4())
        resp = await client.delete(
            f"/api/conversations/{fake_id}",
            cookies=_session_cookie(session_id),
        )
        assert resp.status_code == 404

    async def test_returns_404_for_other_sessions_conversation(
        self, client: AsyncClient, session_id: str, conversation_id: str
    ) -> None:
        resp2 = await client.post("/api/sessions")
        other_session_id = resp2.json()["id"]

        resp = await client.delete(
            f"/api/conversations/{conversation_id}",
            cookies=_session_cookie(other_session_id),
        )
        assert resp.status_code == 404

    async def test_requires_session(self, client: AsyncClient) -> None:
        fake_id = str(uuid.uuid4())
        resp = await client.delete(f"/api/conversations/{fake_id}")
        assert resp.status_code == 401


class TestSendMessage:
    async def test_streams_sse_response(
        self, client: AsyncClient, session_id: str, conversation_id: str
    ) -> None:
        """Test that the message endpoint returns an SSE stream."""

        # Create a mock async event generator
        async def mock_astream_events(input_data, config, version):
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": MagicMock(content="Hello ")},
            }
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": MagicMock(content="world!")},
            }

        mock_graph = MagicMock()
        mock_graph.astream_events = mock_astream_events

        app = client._transport.app  # type: ignore[attr-defined]
        app.state.agent_graph = mock_graph

        resp = await client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "Hello"},
            cookies=_session_cookie(session_id),
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

        # Parse SSE events from the response body
        events = _parse_sse(resp.text)
        token_events = [e for e in events if e["event"] == "token"]
        assert len(token_events) == 2
        assert json.loads(token_events[0]["data"])["content"] == "Hello "
        assert json.loads(token_events[1]["data"])["content"] == "world!"

        # Should have a message_complete at the end
        complete_events = [e for e in events if e["event"] == "message_complete"]
        assert len(complete_events) == 1
        complete_data = json.loads(complete_events[0]["data"])
        assert complete_data["content"] == "Hello world!"

    async def test_streams_tool_events(
        self, client: AsyncClient, session_id: str, conversation_id: str
    ) -> None:
        """Test tool_start and tool_end SSE events."""

        async def mock_astream_events(input_data, config, version):
            yield {
                "event": "on_tool_start",
                "name": "inspect_schema",
                "data": {},
            }
            yield {
                "event": "on_tool_end",
                "name": "inspect_schema",
                "data": {
                    "output": {
                        "table_name": "test_table",
                        "row_count": 100,
                        "columns": [{"name": "id"}, {"name": "val"}],
                    }
                },
            }
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": MagicMock(content="Done.")},
            }

        mock_graph = MagicMock()
        mock_graph.astream_events = mock_astream_events

        app = client._transport.app  # type: ignore[attr-defined]
        app.state.agent_graph = mock_graph

        resp = await client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "Show schema"},
            cookies=_session_cookie(session_id),
        )
        assert resp.status_code == 200
        events = _parse_sse(resp.text)

        tool_starts = [e for e in events if e["event"] == "tool_start"]
        assert len(tool_starts) == 1
        assert json.loads(tool_starts[0]["data"])["tool"] == "inspect_schema"

        tool_ends = [e for e in events if e["event"] == "tool_end"]
        assert len(tool_ends) == 1
        summary = json.loads(tool_ends[0]["data"])["summary"]
        assert "100" in summary
        assert "2 columns" in summary

    async def test_streams_error_on_exception(
        self, client: AsyncClient, session_id: str, conversation_id: str
    ) -> None:
        """Test that errors during streaming produce an error SSE event."""

        async def mock_astream_events(input_data, config, version):
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": MagicMock(content="Partial")},
            }
            raise RuntimeError("LLM connection failed")

        mock_graph = MagicMock()
        mock_graph.astream_events = mock_astream_events

        app = client._transport.app  # type: ignore[attr-defined]
        app.state.agent_graph = mock_graph

        resp = await client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "Test error"},
            cookies=_session_cookie(session_id),
        )
        assert resp.status_code == 200
        events = _parse_sse(resp.text)

        error_events = [e for e in events if e["event"] == "error"]
        assert len(error_events) == 1
        error_data = json.loads(error_events[0]["data"])
        assert "LLM connection failed" in error_data["error"]

    async def test_returns_404_for_nonexistent_conversation(
        self, client: AsyncClient, session_id: str
    ) -> None:
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/conversations/{fake_id}/messages",
            json={"content": "Hello"},
            cookies=_session_cookie(session_id),
        )
        assert resp.status_code == 404

    async def test_returns_404_for_other_sessions_conversation(
        self, client: AsyncClient, session_id: str, conversation_id: str
    ) -> None:
        resp2 = await client.post("/api/sessions")
        other_session_id = resp2.json()["id"]

        resp = await client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "Hello"},
            cookies=_session_cookie(other_session_id),
        )
        assert resp.status_code == 404

    async def test_rejects_empty_message(
        self, client: AsyncClient, session_id: str, conversation_id: str
    ) -> None:
        resp = await client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": ""},
            cookies=_session_cookie(session_id),
        )
        assert resp.status_code == 422

    async def test_requires_session(self, client: AsyncClient) -> None:
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/conversations/{fake_id}/messages",
            json={"content": "Hello"},
        )
        assert resp.status_code == 401


def _parse_sse(text: str) -> list[dict[str, str]]:
    """Parse SSE text into a list of {event, data} dicts.

    Handles both \\n and \\r\\n line endings (sse-starlette uses \\r\\n).
    """
    events = []
    current_event = "message"
    current_data = ""

    for raw_line in text.split("\n"):
        line = raw_line.rstrip("\r")
        if line.startswith("event:"):
            current_event = line[len("event:") :].strip()
        elif line.startswith("data:"):
            current_data = line[len("data:") :].strip()
        elif line == "":
            if current_data:
                events.append({"event": current_event, "data": current_data})
                current_event = "message"
                current_data = ""

    # Handle final event if no trailing newline
    if current_data:
        events.append({"event": current_event, "data": current_data})

    return events
