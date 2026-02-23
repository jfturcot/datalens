import json
import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.dependencies import get_current_session
from app.models import get_db
from app.models.conversation import Conversation
from app.models.schemas import (
    ConversationDetailResponse,
    ConversationMessage,
    ConversationResponse,
    DisplayData,
    MessageRequest,
)
from app.models.session import Session

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_conversation_for_session(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    session: Session,
) -> Conversation:
    """Fetch a conversation and verify it belongs to the given session."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.session_id != session.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    session: Annotated[Session, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ConversationResponse]:
    """List all conversations for the current session."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.session_id == session.id)
        .order_by(Conversation.created_at.desc())
    )
    conversations = result.scalars().all()
    return [ConversationResponse.model_validate(c) for c in conversations]


@router.get(
    "/conversations/{conversation_id}", response_model=ConversationDetailResponse
)
async def get_conversation(
    conversation_id: uuid.UUID,
    session: Annotated[Session, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
) -> ConversationDetailResponse:
    """Get conversation details with message history from LangGraph checkpoints."""
    conversation = await _get_conversation_for_session(db, conversation_id, session)

    # Retrieve message history from LangGraph checkpoints
    messages: list[ConversationMessage] = []
    graph = request.app.state.agent_graph
    config = {"configurable": {"thread_id": str(conversation_id)}}

    try:
        state = await graph.aget_state(config)
        if state and state.values and "messages" in state.values:
            last_sql: str | None = None
            last_query_rows: list[dict[str, Any]] | None = None
            last_present_meta: dict[str, Any] | None = None
            for msg in state.values["messages"]:
                role = getattr(msg, "type", "unknown")
                # Map LangGraph message types to simple roles
                if role == "human":
                    role = "user"
                elif role in ("ai", "AIMessage"):
                    role = "assistant"
                    # Track tool calls across AI messages
                    for tc in getattr(msg, "tool_calls", []):
                        if tc.get("name") == "execute_query":
                            sql = tc.get("args", {}).get("sql")
                            if sql:
                                last_sql = sql
                        elif tc.get("name") == "present_results":
                            last_present_meta = tc.get("args", {})
                elif role == "tool":
                    # Capture execute_query output for data rows
                    tool_name = getattr(msg, "name", "")
                    if tool_name == "execute_query":
                        try:
                            raw = msg.content
                            output = json.loads(raw) if isinstance(raw, str) else raw
                            if isinstance(output, dict) and output.get("success"):
                                last_query_rows = output.get("rows", [])
                        except (json.JSONDecodeError, AttributeError):
                            pass
                    continue  # Skip tool messages in the history

                content = (
                    msg.content if isinstance(msg.content, str) else str(msg.content)
                )
                if content:
                    display_data: DisplayData | None = None
                    sql = None
                    if role == "assistant":
                        # Prefer present_results tool metadata + query data
                        if last_present_meta and last_query_rows is not None:
                            try:
                                display_data = DisplayData(
                                    **last_present_meta,
                                    data=last_query_rows,
                                )
                            except Exception:
                                display_data = None
                        if display_data is None:
                            # Fallback: embedded JSON in content
                            raw_display, content = _extract_display_from_content(
                                content
                            )
                            if raw_display:
                                try:
                                    display_data = DisplayData(**raw_display)
                                except Exception:
                                    display_data = None
                        sql = last_sql
                        last_sql = None
                        last_query_rows = None
                        last_present_meta = None
                    messages.append(
                        ConversationMessage(
                            role=role, content=content, sql=sql, display=display_data
                        )
                    )
    except Exception:
        logger.exception(
            "Failed to retrieve message history for conversation %s", conversation_id
        )
        # Return empty messages rather than failing entirely
        pass

    return ConversationDetailResponse(
        id=conversation.id,
        filename=conversation.filename,
        table_name=conversation.table_name,
        row_count=conversation.row_count,
        created_at=conversation.created_at,
        messages=messages,
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    session: Annotated[Session, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a conversation and its associated data table."""
    conversation = await _get_conversation_for_session(db, conversation_id, session)

    # Drop the data table (use identifier quoting for safety)
    table_name = conversation.table_name
    try:
        await db.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
    except Exception:
        logger.exception("Failed to drop table %s", table_name)
        # Continue with conversation deletion even if table drop fails

    await db.delete(conversation)
    await db.commit()


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: uuid.UUID,
    body: MessageRequest,
    session: Annotated[Session, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
) -> EventSourceResponse:
    """Send a message and stream the agent's response via SSE."""
    # Validate conversation belongs to this session (raises 404 if not)
    await _get_conversation_for_session(db, conversation_id, session)

    graph = request.app.state.agent_graph
    config = {"configurable": {"thread_id": str(conversation_id)}}

    async def event_generator():
        accumulated_content = ""
        # Track tool events during streaming for display construction
        last_query_rows: list[dict[str, Any]] | None = None
        last_query_sql: str | None = None
        present_results_meta: dict[str, Any] | None = None

        try:
            async for event in graph.astream_events(
                {"messages": [("human", body.content)]},
                config=config,
                version="v2",
            ):
                kind = event.get("event", "")

                if kind == "on_chat_model_stream":
                    # Token streaming from the LLM
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        content = chunk.content
                        # Handle list-of-blocks format from Anthropic models
                        if isinstance(content, list):
                            content = "".join(
                                b.get("text", "") if isinstance(b, dict) else str(b)
                                for b in content
                            )
                        if isinstance(content, str) and content:
                            accumulated_content += content
                            yield {
                                "event": "token",
                                "data": json.dumps({"content": content}),
                            }

                elif kind == "on_tool_start":
                    tool_name = event.get("name", "unknown")
                    # Capture present_results args from on_tool_start
                    if tool_name == "present_results":
                        raw_input = event.get("data", {}).get("input", {})
                        if isinstance(raw_input, str):
                            try:
                                raw_input = json.loads(raw_input)
                            except (json.JSONDecodeError, ValueError):
                                raw_input = {}
                        if isinstance(raw_input, dict):
                            present_results_meta = raw_input
                    # Capture SQL from execute_query tool start
                    elif tool_name == "execute_query":
                        tool_input = event.get("data", {}).get("input", {})
                        sql = (
                            tool_input.get("sql")
                            if isinstance(tool_input, dict)
                            else None
                        )
                        if sql:
                            last_query_sql = sql
                    yield {
                        "event": "tool_start",
                        "data": json.dumps({"tool": tool_name}),
                    }

                elif kind == "on_tool_end":
                    tool_name = event.get("name", "unknown")
                    tool_output = event.get("data", {}).get("output", "")
                    # Capture execute_query data rows from on_tool_end
                    # tool_output may be a ToolMessage, dict, or str
                    if tool_name == "execute_query":
                        raw = tool_output
                        if hasattr(raw, "content"):
                            raw = raw.content
                        if isinstance(raw, str):
                            try:
                                raw = json.loads(raw)
                            except (json.JSONDecodeError, ValueError):
                                raw = None
                        if isinstance(raw, dict) and raw.get("success"):
                            last_query_rows = raw.get("rows", [])
                    summary = _summarize_tool_output(tool_output)
                    yield {
                        "event": "tool_end",
                        "data": json.dumps({"summary": summary}),
                    }

            # Build display from present_results + execute_query data
            last_display: dict[str, Any] | None = None
            cleaned_content = accumulated_content

            if present_results_meta and last_query_rows is not None:
                # Structured path: present_results tool was called after
                # execute_query — combine metadata with query data
                last_display = {
                    **present_results_meta,
                    "data": last_query_rows,
                }
            else:
                # Fallback: extract embedded JSON from content
                # (supports old conversations with inline display hints)
                last_display, cleaned_content = _extract_display_from_content(
                    accumulated_content
                )

            if not cleaned_content.strip():
                cleaned_content = (
                    "I wasn't able to generate a complete response. "
                    "Could you try rephrasing your question?"
                )

            # SQL: prefer what we captured from streaming events;
            # fall back to checkpoint state if needed
            last_sql = last_query_sql
            if not last_sql:
                try:
                    state = await graph.aget_state(config)
                    if state and state.values and "messages" in state.values:
                        for msg in reversed(state.values["messages"]):
                            if getattr(msg, "type", None) in (
                                "ai",
                                "AIMessage",
                            ):
                                for tc in getattr(msg, "tool_calls", []):
                                    if tc.get("name") == "execute_query":
                                        sql = tc.get("args", {}).get("sql")
                                        if sql:
                                            last_sql = sql
                                if last_sql:
                                    break
                except Exception:
                    logger.debug("Could not read SQL from checkpoint state")

            complete_data: dict[str, Any] = {"content": cleaned_content}
            if last_sql:
                complete_data["sql"] = last_sql
            if last_display:
                complete_data["display"] = last_display

            yield {
                "event": "message_complete",
                "data": json.dumps(complete_data),
            }

        except Exception as e:
            logger.exception(
                "Error during agent streaming for conversation %s", conversation_id
            )
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    return EventSourceResponse(event_generator())


def _summarize_tool_output(output: Any) -> str:
    """Create a brief summary of tool output for the tool_end event."""
    if isinstance(output, dict):
        if "error" in output:
            return f"Error: {output['error']}"
        if "row_count" in output and "columns" in output:
            return (
                f"Returned {output['row_count']} rows, {len(output['columns'])} columns"
            )
        if "table_name" in output:
            col_count = len(output.get("columns", []))
            rows = output.get("row_count", "?")
            return f"Table {output['table_name']}: {rows} rows, {col_count} columns"
        return json.dumps(output)[:200]
    if isinstance(output, str):
        return output[:200]
    return str(output)[:200]


_DISPLAY_TYPES = frozenset(
    {"text", "table", "bar_chart", "line_chart", "pie_chart", "scatter_plot"}
)


def _unwrap_display(parsed: dict[str, Any]) -> dict[str, Any] | None:
    """Check if parsed JSON is a display hint, unwrapping envelope if needed.

    Handles both direct ``{"type": "bar_chart", ...}`` and wrapped
    ``{"display": {"type": "bar_chart", ...}}`` formats.
    """
    if not isinstance(parsed, dict):
        return None
    if parsed.get("type") in _DISPLAY_TYPES:
        return parsed
    # Unwrap {"display": {...}} envelope
    inner = parsed.get("display")
    if isinstance(inner, dict) and inner.get("type") in _DISPLAY_TYPES:
        return inner
    return None


def _find_brace_balanced_json(text: str, start: int) -> str | None:
    """Extract a brace-balanced JSON substring starting at ``text[start]``.

    Returns the substring from the opening ``{`` through the matching ``}``
    (inclusive), or ``None`` if braces never balance.
    """
    if start >= len(text) or text[start] != "{":
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            if in_string:
                escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _extract_display_from_content(
    content: str,
) -> tuple[dict[str, Any] | None, str]:
    """Extract a display-hint JSON object from the agent's response.

    Returns ``(display_dict, cleaned_content)`` where *cleaned_content* has the
    JSON block (and surrounding fences if present) removed so it doesn't leak
    into the chat bubble.
    """
    import re

    # Strategy 1: fenced code block  ```json { ... } ```
    fence_re = re.compile(r"```(?:json)?\s*\{", re.DOTALL)
    for m in fence_re.finditer(content):
        brace_start = m.end() - 1  # position of the '{'
        blob = _find_brace_balanced_json(content, brace_start)
        if blob is None:
            continue
        try:
            parsed = json.loads(blob)
        except json.JSONDecodeError:
            continue
        display = _unwrap_display(parsed)
        if display is not None:
            # Remove the entire fenced block (``` ... ```)
            block_end = content.find("```", brace_start + len(blob))
            if block_end != -1:
                fence_end = block_end + 3
            else:
                fence_end = brace_start + len(blob)
            cleaned = content[: m.start()] + content[fence_end:]
            return display, cleaned.strip()

    # Strategy 2: bare JSON object with a display type key
    for i in range(len(content)):
        if content[i] != "{":
            continue
        blob = _find_brace_balanced_json(content, i)
        if blob is None:
            continue
        try:
            parsed = json.loads(blob)
        except json.JSONDecodeError:
            continue
        display = _unwrap_display(parsed)
        if display is not None:
            cleaned = content[:i] + content[i + len(blob) :]
            return display, cleaned.strip()

    return None, content
