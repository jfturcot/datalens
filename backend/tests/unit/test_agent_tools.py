"""Unit tests for agent tools: SQL validation, inspect_schema, execute_query."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.tools import (
    _serialize_value,
    execute_query,
    inspect_schema,
    validate_query_sql,
)

# ---------------------------------------------------------------------------
# validate_query_sql – pure logic, no mocking needed
# ---------------------------------------------------------------------------


class TestValidateQuerySql:
    def test_valid_select(self) -> None:
        assert validate_query_sql("SELECT * FROM users") is None

    def test_valid_select_with_where(self) -> None:
        assert validate_query_sql("SELECT name FROM t WHERE id = 1") is None

    def test_valid_select_with_trailing_semicolon(self) -> None:
        assert validate_query_sql("SELECT 1;") is None

    def test_valid_cte(self) -> None:
        sql = "WITH cte AS (SELECT id FROM t) SELECT * FROM cte"
        assert validate_query_sql(sql) is None

    def test_valid_select_with_whitespace(self) -> None:
        assert validate_query_sql("  SELECT 1  ") is None

    def test_empty_query(self) -> None:
        assert validate_query_sql("") == "Empty query."
        assert validate_query_sql("   ") == "Empty query."
        assert validate_query_sql(";") == "Empty query."

    def test_reject_insert(self) -> None:
        result = validate_query_sql("INSERT INTO t VALUES (1)")
        assert result is not None
        assert "Only SELECT" in result

    def test_reject_update(self) -> None:
        result = validate_query_sql("UPDATE t SET x = 1")
        assert result is not None
        assert "Only SELECT" in result

    def test_reject_delete(self) -> None:
        result = validate_query_sql("DELETE FROM t")
        assert result is not None
        assert "Only SELECT" in result

    def test_reject_drop(self) -> None:
        result = validate_query_sql("DROP TABLE t")
        assert result is not None
        assert "Only SELECT" in result

    def test_reject_alter(self) -> None:
        result = validate_query_sql("ALTER TABLE t ADD col int")
        assert result is not None
        assert "Only SELECT" in result

    def test_reject_create(self) -> None:
        result = validate_query_sql("CREATE TABLE t (id int)")
        assert result is not None
        assert "Only SELECT" in result

    def test_reject_truncate(self) -> None:
        result = validate_query_sql("TRUNCATE t")
        assert result is not None
        assert "Only SELECT" in result

    def test_reject_multi_statement(self) -> None:
        result = validate_query_sql("SELECT 1; DROP TABLE t")
        assert result is not None
        assert "Multiple statements" in result

    def test_reject_select_with_embedded_drop(self) -> None:
        result = validate_query_sql("SELECT * FROM t WHERE name = 'DROP'")
        assert result is not None
        assert "forbidden keyword" in result.lower()

    def test_reject_case_insensitive(self) -> None:
        result = validate_query_sql("select * from t; delete from t")
        assert result is not None

    def test_reject_non_select_start(self) -> None:
        result = validate_query_sql("EXPLAIN SELECT 1")
        assert result is not None
        assert "Only SELECT" in result

    def test_reject_forbidden_keyword_in_cte(self) -> None:
        result = validate_query_sql("WITH x AS (SELECT 1) DELETE FROM t")
        assert result is not None
        assert "forbidden keyword" in result.lower()


# ---------------------------------------------------------------------------
# _serialize_value – type conversion
# ---------------------------------------------------------------------------


class TestSerializeValue:
    def test_none(self) -> None:
        assert _serialize_value(None) is None

    def test_decimal(self) -> None:
        assert _serialize_value(Decimal("3.14")) == 3.14

    def test_int(self) -> None:
        assert _serialize_value(42) == 42

    def test_str(self) -> None:
        assert _serialize_value("hello") == "hello"


# ---------------------------------------------------------------------------
# Helper to build a mock psycopg async connection + cursor
#
# psycopg v3 patterns:
#   await psycopg.AsyncConnection.connect(...)  -> returns conn (async CM)
#   conn.cursor()  -> sync call, returns AsyncCursor (async CM)
#   cursor.execute / fetchall / fetchone / fetchmany  -> all async
# ---------------------------------------------------------------------------


def _make_mock_conn(
    fetchall_results: list[list[tuple]] | None = None,
    fetchone_results: list[tuple | None] | None = None,
    fetchmany_result: list[tuple] | None = None,
    description: list[tuple] | None = None,
):
    """Return (mock_connect_coroutine, mock_cursor)."""
    call_idx = {"value": 0}

    # Build cursor as MagicMock with async methods
    cursor = MagicMock()
    cursor.__aenter__ = AsyncMock(return_value=cursor)
    cursor.__aexit__ = AsyncMock(return_value=False)

    async def _execute(*_a, **_kw):
        call_idx["value"] += 1

    cursor.execute = _execute

    if fetchall_results is not None:

        async def _fetchall():
            idx = call_idx["value"] - 1
            if idx < len(fetchall_results):
                return fetchall_results[idx]
            return []

        cursor.fetchall = _fetchall

    if fetchone_results is not None:

        async def _fetchone():
            idx = call_idx["value"] - 1
            if idx < len(fetchone_results):
                return fetchone_results[idx]
            return None

        cursor.fetchone = _fetchone

    if fetchmany_result is not None:
        cursor.fetchmany = AsyncMock(return_value=fetchmany_result)

    if description is not None:
        cursor.description = description

    # Build connection as MagicMock with async CM support
    conn = MagicMock()
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=False)
    conn.cursor = MagicMock(return_value=cursor)  # sync call

    # connect() is awaited: returns conn
    async_connect = AsyncMock(return_value=conn)

    return async_connect, cursor


# ---------------------------------------------------------------------------
# inspect_schema – mocked database
# ---------------------------------------------------------------------------


class TestInspectSchema:
    @pytest.mark.asyncio
    async def test_returns_schema_for_valid_table(self) -> None:
        # Call sequence (call_idx after each execute):
        #   execute #1 (idx=1): columns query     -> fetchall reads idx 0
        #   execute #2 (idx=2): row count          -> fetchone reads idx 1
        #   execute #3 (idx=3): text samples       -> fetchall reads idx 2
        #   execute #4 (idx=4): numeric stats      -> fetchone reads idx 3
        mock_connect, _ = _make_mock_conn(
            fetchall_results=[
                [("name", "text"), ("age", "integer")],  # idx 0
                [],  # idx 1 (unused)
                [("Alice",), ("Bob",), ("Carol",)],  # idx 2
            ],
            fetchone_results=[
                None,  # idx 0 (unused)
                (42,),  # idx 1: row count
                None,  # idx 2 (unused)
                (18, 65, 35.5),  # idx 3: numeric stats
            ],
        )

        with patch("app.agent.tools.psycopg.AsyncConnection.connect", mock_connect):
            result = await inspect_schema.ainvoke({"table_name": "test_table"})

        assert result["table_name"] == "test_table"
        assert result["row_count"] == 42
        assert len(result["columns"]) == 2
        assert result["columns"][0]["name"] == "name"
        assert result["columns"][0]["type"] == "text"
        assert result["columns"][0]["sample_values"] == ["Alice", "Bob", "Carol"]
        assert result["columns"][1]["name"] == "age"
        assert result["columns"][1]["min"] == 18.0
        assert result["columns"][1]["max"] == 65.0
        assert result["columns"][1]["mean"] == 35.5

    @pytest.mark.asyncio
    async def test_returns_error_for_nonexistent_table(self) -> None:
        mock_connect, _ = _make_mock_conn(
            fetchall_results=[[]],
        )

        with patch("app.agent.tools.psycopg.AsyncConnection.connect", mock_connect):
            result = await inspect_schema.ainvoke({"table_name": "no_such_table"})

        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_error_on_db_failure(self) -> None:
        mock_connect = AsyncMock(side_effect=Exception("connection refused"))

        with patch("app.agent.tools.psycopg.AsyncConnection.connect", mock_connect):
            result = await inspect_schema.ainvoke({"table_name": "t"})

        assert "error" in result
        assert "Failed to inspect schema" in result["error"]


# ---------------------------------------------------------------------------
# execute_query – SQL validation + mocked database
# ---------------------------------------------------------------------------


class TestExecuteQuery:
    @pytest.mark.asyncio
    async def test_rejects_insert(self) -> None:
        result = await execute_query.ainvoke({"sql": "INSERT INTO t VALUES (1)"})
        assert result["success"] is False
        assert "Only SELECT" in result["error"]

    @pytest.mark.asyncio
    async def test_rejects_drop(self) -> None:
        result = await execute_query.ainvoke({"sql": "DROP TABLE t"})
        assert result["success"] is False
        assert "Only SELECT" in result["error"]

    @pytest.mark.asyncio
    async def test_rejects_update(self) -> None:
        result = await execute_query.ainvoke({"sql": "UPDATE t SET x = 1"})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_rejects_delete(self) -> None:
        result = await execute_query.ainvoke({"sql": "DELETE FROM t"})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_rejects_truncate(self) -> None:
        result = await execute_query.ainvoke({"sql": "TRUNCATE t"})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_rejects_create(self) -> None:
        result = await execute_query.ainvoke({"sql": "CREATE TABLE t (id int)"})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_rejects_alter(self) -> None:
        result = await execute_query.ainvoke({"sql": "ALTER TABLE t ADD col int"})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_rejects_empty(self) -> None:
        result = await execute_query.ainvoke({"sql": ""})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_rejects_multi_statement(self) -> None:
        result = await execute_query.ainvoke({"sql": "SELECT 1; DROP TABLE t"})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_successful_select(self) -> None:
        mock_connect, cursor = _make_mock_conn(
            fetchmany_result=[(1, "Alice"), (2, "Bob")],
            description=[("id",), ("name",)],
        )

        with patch("app.agent.tools.psycopg.AsyncConnection.connect", mock_connect):
            result = await execute_query.ainvoke({"sql": "SELECT id, name FROM users"})

        assert result["success"] is True
        assert result["row_count"] == 2
        assert result["columns"] == ["id", "name"]
        assert result["rows"][0] == {"id": 1, "name": "Alice"}

    @pytest.mark.asyncio
    async def test_returns_error_on_db_exception(self) -> None:
        mock_connect = AsyncMock(side_effect=Exception("connection refused"))

        with patch("app.agent.tools.psycopg.AsyncConnection.connect", mock_connect):
            result = await execute_query.ainvoke({"sql": "SELECT 1"})

        assert result["success"] is False
        assert "connection refused" in result["error"]
