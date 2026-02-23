"""Unit tests for _repair_orphaned_tool_calls checkpoint self-healing."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.routes.conversations import _repair_orphaned_tool_calls


def _make_ai_msg(tool_calls: list[dict] | None = None, content: str = "") -> MagicMock:
    msg = MagicMock()
    msg.type = "ai"
    msg.content = content
    msg.tool_calls = tool_calls or []
    return msg


def _make_tool_msg(tool_call_id: str, name: str = "test_tool") -> MagicMock:
    msg = MagicMock()
    msg.type = "tool"
    msg.tool_call_id = tool_call_id
    msg.name = name
    msg.content = '{"result": "ok"}'
    return msg


def _make_human_msg(content: str = "Hello") -> MagicMock:
    msg = MagicMock()
    msg.type = "human"
    msg.content = content
    return msg


def _make_graph(messages: list) -> MagicMock:
    """Create a mock graph with the given messages in its checkpoint state."""
    graph = MagicMock()
    state = MagicMock()
    state.values = {"messages": messages}
    graph.aget_state = AsyncMock(return_value=state)
    graph.aupdate_state = AsyncMock()
    return graph


CONFIG = {"configurable": {"thread_id": "test-thread"}}


class TestRepairOrphanedToolCalls:
    @pytest.mark.asyncio
    async def test_injects_synthetic_tool_message_for_orphaned_call(self) -> None:
        """An AIMessage with tool_calls and no ToolMessages triggers repair."""
        ai_msg = _make_ai_msg(
            tool_calls=[
                {"id": "call_1", "name": "execute_query", "args": {"sql": "SELECT 1"}},
            ]
        )
        graph = _make_graph([_make_human_msg(), ai_msg])

        await _repair_orphaned_tool_calls(graph, CONFIG)

        graph.aupdate_state.assert_called_once()
        call_args = graph.aupdate_state.call_args
        assert call_args[0][0] == CONFIG
        injected = call_args[0][1]["messages"]
        assert len(injected) == 1
        assert injected[0].tool_call_id == "call_1"
        assert injected[0].name == "execute_query"
        assert "interrupted" in injected[0].content.lower()
        assert call_args[1]["as_node"] == "tools"

    @pytest.mark.asyncio
    async def test_injects_for_multiple_orphaned_calls(self) -> None:
        """Multiple orphaned tool_calls each get a synthetic ToolMessage."""
        ai_msg = _make_ai_msg(
            tool_calls=[
                {"id": "call_1", "name": "inspect_schema", "args": {}},
                {"id": "call_2", "name": "execute_query", "args": {"sql": "SELECT 1"}},
            ]
        )
        graph = _make_graph([_make_human_msg(), ai_msg])

        await _repair_orphaned_tool_calls(graph, CONFIG)

        graph.aupdate_state.assert_called_once()
        injected = graph.aupdate_state.call_args[0][1]["messages"]
        assert len(injected) == 2
        assert {m.tool_call_id for m in injected} == {"call_1", "call_2"}

    @pytest.mark.asyncio
    async def test_does_not_modify_clean_checkpoint(self) -> None:
        """Checkpoint with matched tool_calls and ToolMessages is left alone."""
        ai_msg = _make_ai_msg(
            tool_calls=[
                {"id": "call_1", "name": "execute_query", "args": {"sql": "SELECT 1"}},
            ]
        )
        tool_msg = _make_tool_msg("call_1", "execute_query")
        final_ai = _make_ai_msg(content="The result is 1.")

        graph = _make_graph([_make_human_msg(), ai_msg, tool_msg, final_ai])

        await _repair_orphaned_tool_calls(graph, CONFIG)

        graph.aupdate_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_modify_checkpoint_ending_with_human(self) -> None:
        """Checkpoint ending with a human message needs no repair."""
        graph = _make_graph([_make_human_msg()])

        await _repair_orphaned_tool_calls(graph, CONFIG)

        graph.aupdate_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_modify_empty_checkpoint(self) -> None:
        """Empty message list triggers no repair."""
        graph = _make_graph([])

        await _repair_orphaned_tool_calls(graph, CONFIG)

        graph.aupdate_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_modify_ai_without_tool_calls(self) -> None:
        """AIMessage with no tool_calls triggers no repair."""
        ai_msg = _make_ai_msg(content="Hello!")
        graph = _make_graph([_make_human_msg(), ai_msg])

        await _repair_orphaned_tool_calls(graph, CONFIG)

        graph.aupdate_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_partial_orphan(self) -> None:
        """Only the unanswered tool_call gets a synthetic message."""
        ai_msg = _make_ai_msg(
            tool_calls=[
                {"id": "call_1", "name": "inspect_schema", "args": {}},
                {"id": "call_2", "name": "execute_query", "args": {"sql": "SELECT 1"}},
            ]
        )
        # Only call_1 got a response before the crash
        tool_msg = _make_tool_msg("call_1", "inspect_schema")

        graph = _make_graph([_make_human_msg(), ai_msg, tool_msg])

        await _repair_orphaned_tool_calls(graph, CONFIG)

        graph.aupdate_state.assert_called_once()
        injected = graph.aupdate_state.call_args[0][1]["messages"]
        assert len(injected) == 1
        assert injected[0].tool_call_id == "call_2"

    @pytest.mark.asyncio
    async def test_gracefully_handles_aget_state_failure(self) -> None:
        """If aget_state raises, repair is silently skipped."""
        graph = MagicMock()
        graph.aget_state = AsyncMock(side_effect=RuntimeError("DB down"))
        graph.aupdate_state = AsyncMock()

        await _repair_orphaned_tool_calls(graph, CONFIG)

        graph.aupdate_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_gracefully_handles_none_state(self) -> None:
        """If aget_state returns None, repair is skipped."""
        graph = MagicMock()
        graph.aget_state = AsyncMock(return_value=None)
        graph.aupdate_state = AsyncMock()

        await _repair_orphaned_tool_calls(graph, CONFIG)

        graph.aupdate_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_gracefully_handles_empty_values(self) -> None:
        """If state.values is empty, repair is skipped."""
        graph = MagicMock()
        state = MagicMock()
        state.values = {}
        graph.aget_state = AsyncMock(return_value=state)
        graph.aupdate_state = AsyncMock()

        await _repair_orphaned_tool_calls(graph, CONFIG)

        graph.aupdate_state.assert_not_called()
