"""Unit tests for display extraction from streaming events and content fallback.

Tests cover:
- present_results tool metadata + execute_query data combination
- Gating: no display when execute_query not called
- Fallback: old conversations with embedded JSON still work
- History reconstruction with present_results tool calls
"""

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.routes.conversations import _extract_display_from_content

# ---------------------------------------------------------------------------
# Helper to simulate streaming event_generator logic
# ---------------------------------------------------------------------------


async def _simulate_streaming(
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Simulate the event_generator logic from send_message.

    Takes a list of mock stream events and returns the message_complete data.
    This mirrors the streaming extraction logic in conversations.py.
    """
    accumulated_content = ""
    last_query_rows: list[dict[str, Any]] | None = None
    last_query_sql: str | None = None
    present_results_meta: dict[str, Any] | None = None

    for event in events:
        kind = event.get("event", "")

        if kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                content = chunk.content
                if isinstance(content, str) and content:
                    accumulated_content += content

        elif kind == "on_tool_start":
            tool_name = event.get("name", "unknown")
            if tool_name == "present_results":
                present_results_meta = event.get("data", {}).get("input", {})
            elif tool_name == "execute_query":
                tool_input = event.get("data", {}).get("input", {})
                sql = tool_input.get("sql") if isinstance(tool_input, dict) else None
                if sql:
                    last_query_sql = sql

        elif kind == "on_tool_end":
            tool_name = event.get("name", "unknown")
            tool_output = event.get("data", {}).get("output", "")
            if tool_name == "execute_query" and isinstance(tool_output, dict):
                if tool_output.get("success"):
                    last_query_rows = tool_output.get("rows", [])

    # Build display
    last_display: dict[str, Any] | None = None
    cleaned_content = accumulated_content

    if present_results_meta and last_query_rows is not None:
        last_display = {**present_results_meta, "data": last_query_rows}
    else:
        last_display, cleaned_content = _extract_display_from_content(
            accumulated_content
        )

    complete_data: dict[str, Any] = {"content": cleaned_content}
    if last_query_sql:
        complete_data["sql"] = last_query_sql
    if last_display:
        complete_data["display"] = last_display

    return complete_data


def _chunk(text: str) -> dict[str, Any]:
    """Create an on_chat_model_stream event."""
    mock = MagicMock()
    mock.content = text
    return {"event": "on_chat_model_stream", "data": {"chunk": mock}}


def _tool_start(name: str, input_data: dict[str, Any]) -> dict[str, Any]:
    """Create an on_tool_start event."""
    return {"event": "on_tool_start", "name": name, "data": {"input": input_data}}


def _tool_end(name: str, output: Any) -> dict[str, Any]:
    """Create an on_tool_end event."""
    return {"event": "on_tool_end", "name": name, "data": {"output": output}}


# ---------------------------------------------------------------------------
# Test: present_results + execute_query produces display
# ---------------------------------------------------------------------------


class TestStreamingDisplayExtraction:
    @pytest.mark.asyncio
    async def test_present_results_with_execute_query(self) -> None:
        """Display IS returned when execute_query + present_results both called."""
        rows = [{"region": "East", "sales": 100}, {"region": "West", "sales": 200}]
        events = [
            _tool_start("execute_query", {"sql": "SELECT region, sales FROM t"}),
            _tool_end(
                "execute_query",
                {
                    "success": True,
                    "row_count": 2,
                    "columns": ["region", "sales"],
                    "rows": rows,
                },
            ),
            _tool_start(
                "present_results",
                {
                    "type": "bar_chart",
                    "title": "Sales",
                    "x_axis": "region",
                    "y_axis": "sales",
                },
            ),
            _tool_end(
                "present_results", {"success": True, "display": {"type": "bar_chart"}}
            ),
            _chunk("Here are the sales by region."),
        ]

        result = await _simulate_streaming(events)

        assert result["sql"] == "SELECT region, sales FROM t"
        assert result["display"] is not None
        assert result["display"]["type"] == "bar_chart"
        assert result["display"]["title"] == "Sales"
        assert result["display"]["x_axis"] == "region"
        assert result["display"]["y_axis"] == "sales"
        assert result["display"]["data"] == rows
        # Content should NOT be cleaned (no embedded JSON to strip)
        assert result["content"] == "Here are the sales by region."

    @pytest.mark.asyncio
    async def test_no_display_without_execute_query(self) -> None:
        """No display when only inspect_schema called."""
        events = [
            _tool_start("inspect_schema", {"table_name": "users"}),
            _tool_end(
                "inspect_schema",
                {"table_name": "users", "row_count": 50, "columns": [{"name": "id"}]},
            ),
            # present_results called without prior execute_query
            _tool_start("present_results", {"type": "table"}),
            _tool_end(
                "present_results", {"success": True, "display": {"type": "table"}}
            ),
            _chunk("The users table has 50 rows."),
        ]

        result = await _simulate_streaming(events)

        # No display because execute_query was never called (no data rows)
        assert "display" not in result
        assert result["content"] == "The users table has 50 rows."

    @pytest.mark.asyncio
    async def test_no_display_without_present_results(self) -> None:
        """No display when execute_query called but present_results not called,
        and no embedded JSON in content."""
        events = [
            _tool_start("execute_query", {"sql": "SELECT COUNT(*) FROM t"}),
            _tool_end(
                "execute_query",
                {
                    "success": True,
                    "row_count": 1,
                    "columns": ["count"],
                    "rows": [{"count": 42}],
                },
            ),
            _chunk("There are 42 rows."),
        ]

        result = await _simulate_streaming(events)

        # No present_results and no embedded JSON → no display
        assert "display" not in result
        assert result["content"] == "There are 42 rows."

    @pytest.mark.asyncio
    async def test_failed_execute_query_no_display(self) -> None:
        """No display when execute_query failed (success=False)."""
        events = [
            _tool_start("execute_query", {"sql": "SELECT bad FROM t"}),
            _tool_end("execute_query", {"success": False, "error": "column not found"}),
            _tool_start("present_results", {"type": "table"}),
            _tool_end(
                "present_results", {"success": True, "display": {"type": "table"}}
            ),
            _chunk("The query failed."),
        ]

        result = await _simulate_streaming(events)

        # execute_query failed, so no rows captured → no display
        assert "display" not in result

    @pytest.mark.asyncio
    async def test_pie_chart_metadata(self) -> None:
        """Pie chart with label_key and value_key passes through correctly."""
        rows = [{"cat": "A", "val": 10}, {"cat": "B", "val": 20}]
        events = [
            _tool_start("execute_query", {"sql": "SELECT cat, val FROM t"}),
            _tool_end(
                "execute_query",
                {
                    "success": True,
                    "row_count": 2,
                    "columns": ["cat", "val"],
                    "rows": rows,
                },
            ),
            _tool_start(
                "present_results",
                {
                    "type": "pie_chart",
                    "title": "Distribution",
                    "label_key": "cat",
                    "value_key": "val",
                },
            ),
            _tool_end(
                "present_results", {"success": True, "display": {"type": "pie_chart"}}
            ),
            _chunk("Here's the distribution."),
        ]

        result = await _simulate_streaming(events)

        assert result["display"]["type"] == "pie_chart"
        assert result["display"]["label_key"] == "cat"
        assert result["display"]["value_key"] == "val"
        assert result["display"]["data"] == rows

    @pytest.mark.asyncio
    async def test_sql_captured_from_streaming(self) -> None:
        """SQL is captured from on_tool_start events during streaming."""
        events = [
            _tool_start("execute_query", {"sql": "SELECT id FROM users"}),
            _tool_end(
                "execute_query",
                {
                    "success": True,
                    "row_count": 1,
                    "columns": ["id"],
                    "rows": [{"id": 1}],
                },
            ),
            _chunk("Found one user."),
        ]

        result = await _simulate_streaming(events)
        assert result["sql"] == "SELECT id FROM users"

    @pytest.mark.asyncio
    async def test_multiple_queries_uses_last(self) -> None:
        """When multiple execute_query calls, uses the last one's data."""
        rows1 = [{"x": 1}]
        rows2 = [{"y": 2}, {"y": 3}]
        events = [
            _tool_start("execute_query", {"sql": "SELECT x FROM a"}),
            _tool_end(
                "execute_query",
                {"success": True, "row_count": 1, "columns": ["x"], "rows": rows1},
            ),
            _tool_start("execute_query", {"sql": "SELECT y FROM b"}),
            _tool_end(
                "execute_query",
                {"success": True, "row_count": 2, "columns": ["y"], "rows": rows2},
            ),
            _tool_start("present_results", {"type": "table"}),
            _tool_end(
                "present_results", {"success": True, "display": {"type": "table"}}
            ),
            _chunk("Results."),
        ]

        result = await _simulate_streaming(events)

        assert result["sql"] == "SELECT y FROM b"
        assert result["display"]["data"] == rows2


# ---------------------------------------------------------------------------
# Test: fallback to embedded JSON for old conversations
# ---------------------------------------------------------------------------


class TestFallbackEmbeddedJson:
    @pytest.mark.asyncio
    async def test_embedded_json_in_fenced_block(self) -> None:
        """Old conversations with ```json display blocks still work."""
        content_with_json = (
            'Here are the results.\n\n```json\n{"type": "bar_chart", '
            '"title": "Sales", "x_axis": "region", "y_axis": "total", '
            '"data": [{"region": "East", "total": 100}]}\n```'
        )
        events = [_chunk(content_with_json)]

        result = await _simulate_streaming(events)

        assert result["display"] is not None
        assert result["display"]["type"] == "bar_chart"
        assert result["display"]["title"] == "Sales"
        assert "```" not in result["content"]

    @pytest.mark.asyncio
    async def test_embedded_bare_json(self) -> None:
        """Old conversations with bare JSON display objects still work."""
        content_with_json = (
            'The answer is 42. {"type": "text", "data": [{"count": 42}]}'
        )
        events = [_chunk(content_with_json)]

        result = await _simulate_streaming(events)

        assert result["display"] is not None
        assert result["display"]["type"] == "text"


# ---------------------------------------------------------------------------
# Test: history reconstruction with present_results tool calls
# ---------------------------------------------------------------------------


class TestHistoryReconstructionWithPresentResults:
    def _make_ai_msg(
        self,
        content: str = "",
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> MagicMock:
        msg = MagicMock()
        msg.type = "ai"
        msg.content = content
        msg.tool_calls = tool_calls or []
        return msg

    def _make_tool_msg(self, name: str, content: Any) -> MagicMock:
        msg = MagicMock()
        msg.type = "tool"
        msg.name = name
        msg.content = json.dumps(content) if isinstance(content, dict) else content
        return msg

    def _make_human_msg(self, content: str) -> MagicMock:
        msg = MagicMock()
        msg.type = "human"
        msg.content = content
        return msg

    def _reconstruct_history(
        self,
        messages: list[MagicMock],
    ) -> list[dict[str, Any]]:
        """Simulate the history reconstruction logic from get_conversation."""
        from app.models.schemas import DisplayData

        result: list[dict[str, Any]] = []
        last_sql: str | None = None
        last_query_rows: list[dict[str, Any]] | None = None
        last_present_meta: dict[str, Any] | None = None

        for msg in messages:
            role = getattr(msg, "type", "unknown")
            if role == "human":
                role = "user"
            elif role in ("ai", "AIMessage"):
                role = "assistant"
                for tc in getattr(msg, "tool_calls", []):
                    if tc.get("name") == "execute_query":
                        sql = tc.get("args", {}).get("sql")
                        if sql:
                            last_sql = sql
                    elif tc.get("name") == "present_results":
                        last_present_meta = tc.get("args", {})
            elif role == "tool":
                tool_name = getattr(msg, "name", "")
                if tool_name == "execute_query":
                    try:
                        raw = msg.content
                        output = json.loads(raw) if isinstance(raw, str) else raw
                        if isinstance(output, dict) and output.get("success"):
                            last_query_rows = output.get("rows", [])
                    except (json.JSONDecodeError, AttributeError):
                        pass
                continue

            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            if content:
                display_data = None
                sql = None
                if role == "assistant":
                    if last_present_meta and last_query_rows is not None:
                        try:
                            display_data = DisplayData(
                                **last_present_meta, data=last_query_rows
                            ).model_dump()
                        except Exception:
                            display_data = None
                    if display_data is None:
                        raw_display, content = _extract_display_from_content(content)
                        if raw_display:
                            try:
                                display_data = DisplayData(**raw_display).model_dump()
                            except Exception:
                                display_data = None
                    sql = last_sql
                    last_sql = None
                    last_query_rows = None
                    last_present_meta = None
                result.append(
                    {
                        "role": role,
                        "content": content,
                        "sql": sql,
                        "display": display_data,
                    }
                )

        return result

    def test_present_results_in_history(self) -> None:
        """History reconstruction picks up present_results tool calls."""
        rows = [{"region": "East", "sales": 100}]
        msgs = [
            self._make_human_msg("Show sales"),
            # AI calls execute_query
            self._make_ai_msg(
                tool_calls=[
                    {
                        "name": "execute_query",
                        "args": {"sql": "SELECT region, sales FROM t"},
                    }
                ]
            ),
            # Tool response for execute_query
            self._make_tool_msg(
                "execute_query",
                {
                    "success": True,
                    "row_count": 1,
                    "columns": ["region", "sales"],
                    "rows": rows,
                },
            ),
            # AI calls present_results
            self._make_ai_msg(
                tool_calls=[
                    {
                        "name": "present_results",
                        "args": {
                            "type": "bar_chart",
                            "title": "Sales",
                            "x_axis": "region",
                            "y_axis": "sales",
                        },
                    }
                ]
            ),
            # Tool response for present_results
            self._make_tool_msg("present_results", {"success": True}),
            # Final AI message with content
            self._make_ai_msg("Here are the sales by region."),
        ]

        result = self._reconstruct_history(msgs)

        # Should have user + assistant messages
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assistant_msg = result[1]
        assert assistant_msg["role"] == "assistant"
        assert assistant_msg["sql"] == "SELECT region, sales FROM t"
        assert assistant_msg["display"] is not None
        assert assistant_msg["display"]["type"] == "bar_chart"
        assert assistant_msg["display"]["data"] == rows

    def test_old_embedded_json_history(self) -> None:
        """Old conversations with embedded JSON still render via fallback."""
        msgs = [
            self._make_human_msg("Count rows"),
            self._make_ai_msg(
                tool_calls=[
                    {"name": "execute_query", "args": {"sql": "SELECT COUNT(*) FROM t"}}
                ]
            ),
            self._make_tool_msg(
                "execute_query",
                {
                    "success": True,
                    "row_count": 1,
                    "columns": ["count"],
                    "rows": [{"count": 42}],
                },
            ),
            # Old-style: final AI message embeds display JSON in content
            self._make_ai_msg(
                'There are 42 rows. {"type": "text", "data": [{"count": 42}]}'
            ),
        ]

        result = self._reconstruct_history(msgs)

        assert len(result) == 2
        assistant_msg = result[1]
        assert assistant_msg["display"] is not None
        assert assistant_msg["display"]["type"] == "text"
        # Content should have JSON stripped
        assert "{" not in assistant_msg["content"]

    def test_no_display_inspect_schema_only(self) -> None:
        """No display when only inspect_schema was called in history."""
        msgs = [
            self._make_human_msg("What tables exist?"),
            self._make_ai_msg(
                tool_calls=[{"name": "inspect_schema", "args": {"table_name": "users"}}]
            ),
            self._make_tool_msg(
                "inspect_schema",
                {"table_name": "users", "row_count": 50, "columns": []},
            ),
            self._make_ai_msg("The users table has 50 rows."),
        ]

        result = self._reconstruct_history(msgs)

        assert len(result) == 2
        assistant_msg = result[1]
        assert assistant_msg["display"] is None
        assert assistant_msg["sql"] is None
