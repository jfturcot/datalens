import datetime as dt
import decimal
import logging
import re
import uuid
from typing import Any

import psycopg
from langchain_core.tools import tool
from psycopg import sql as psycopg_sql

from app.config import settings

logger = logging.getLogger(__name__)

FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b",
    re.IGNORECASE,
)

NUMERIC_TYPES = frozenset(
    {
        "integer",
        "bigint",
        "smallint",
        "numeric",
        "real",
        "double precision",
        "float",
        "decimal",
    }
)

TEXT_TYPES = frozenset(
    {
        "text",
        "character varying",
        "varchar",
        "char",
        "character",
    }
)


def _get_conninfo() -> str:
    """Build psycopg connection string from settings."""
    return (
        f"host={settings.postgres_host} port={settings.postgres_port} "
        f"dbname={settings.postgres_db} user={settings.postgres_user} "
        f"password={settings.postgres_password}"
    )


def _serialize_value(val: Any) -> Any:
    """Convert database values to JSON-serializable types."""
    if val is None:
        return None
    if isinstance(val, decimal.Decimal):
        return float(val)
    if isinstance(val, (dt.date, dt.datetime)):
        return val.isoformat()
    if isinstance(val, uuid.UUID):
        return str(val)
    return val


def validate_query_sql(sql_str: str) -> str | None:
    """Validate that SQL is a read-only SELECT query.

    Returns None if valid, or an error message string if invalid.
    """
    stripped = sql_str.strip().rstrip(";").strip()

    if not stripped:
        return "Empty query."

    # Reject multi-statement queries
    if ";" in stripped:
        return "Multiple statements are not allowed."

    # Must start with SELECT or WITH (CTE)
    upper = stripped.upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        return "Only SELECT queries are allowed."

    # Check for forbidden keywords
    match = FORBIDDEN_KEYWORDS.search(stripped)
    if match:
        return (
            f"Query contains forbidden keyword: {match.group(0).upper()}. "
            "Only SELECT queries are allowed."
        )

    return None


@tool
async def inspect_schema(table_name: str) -> dict[str, Any]:
    """Returns the schema of a table in the database including column names,
    types, row count, and statistics. For text columns includes up to 5
    sample unique values. For numeric columns includes min, max, mean."""

    conninfo = _get_conninfo()
    try:
        async with await psycopg.AsyncConnection.connect(conninfo) as conn:
            async with conn.cursor() as cur:
                # Get column info from information_schema
                await cur.execute(
                    "SELECT column_name, data_type "
                    "FROM information_schema.columns "
                    "WHERE table_name = %s "
                    "ORDER BY ordinal_position",
                    (table_name,),
                )
                columns_raw = await cur.fetchall()

                if not columns_raw:
                    return {"error": f"Table '{table_name}' not found."}

                # Get row count
                count_q = psycopg_sql.SQL("SELECT COUNT(*) FROM {}").format(
                    psycopg_sql.Identifier(table_name)
                )
                await cur.execute(count_q)
                row = await cur.fetchone()
                row_count = row[0] if row else 0

                columns: list[dict[str, Any]] = []
                for col_name, data_type in columns_raw:
                    col_info: dict[str, Any] = {
                        "name": col_name,
                        "type": data_type,
                    }

                    if data_type in TEXT_TYPES:
                        sample_q = psycopg_sql.SQL(
                            "SELECT DISTINCT {} FROM {} WHERE {} IS NOT NULL LIMIT 5"
                        ).format(
                            psycopg_sql.Identifier(col_name),
                            psycopg_sql.Identifier(table_name),
                            psycopg_sql.Identifier(col_name),
                        )
                        await cur.execute(sample_q)
                        samples = [r[0] for r in await cur.fetchall()]
                        col_info["sample_values"] = samples

                    elif data_type in NUMERIC_TYPES:
                        stats_q = psycopg_sql.SQL(
                            "SELECT MIN({}), MAX({}), AVG({}) FROM {}"
                        ).format(
                            psycopg_sql.Identifier(col_name),
                            psycopg_sql.Identifier(col_name),
                            psycopg_sql.Identifier(col_name),
                            psycopg_sql.Identifier(table_name),
                        )
                        await cur.execute(stats_q)
                        stats_row = await cur.fetchone()
                        if stats_row:
                            col_info["min"] = (
                                float(stats_row[0])
                                if stats_row[0] is not None
                                else None
                            )
                            col_info["max"] = (
                                float(stats_row[1])
                                if stats_row[1] is not None
                                else None
                            )
                            col_info["mean"] = (
                                round(float(stats_row[2]), 2)
                                if stats_row[2] is not None
                                else None
                            )

                    columns.append(col_info)

                return {
                    "table_name": table_name,
                    "row_count": row_count,
                    "columns": columns,
                }
    except Exception as e:
        logger.exception("Error inspecting schema for table %s", table_name)
        return {"error": f"Failed to inspect schema: {e}"}


@tool
async def execute_query(sql: str) -> dict[str, Any]:
    """Executes a read-only SQL query against the database.
    The query MUST be a SELECT statement. No INSERT, UPDATE, DELETE, DROP,
    ALTER, CREATE, or TRUNCATE. Maximum 500 rows returned. Queries timeout
    after 10 seconds."""

    # Validate
    error = validate_query_sql(sql)
    if error:
        return {"success": False, "error": error}

    cleaned = sql.strip().rstrip(";").strip()

    # Add LIMIT if not present
    if "LIMIT" not in cleaned.upper():
        cleaned = f"{cleaned} LIMIT 500"

    conninfo = _get_conninfo()
    try:
        async with await psycopg.AsyncConnection.connect(
            conninfo, autocommit=True
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute("SET statement_timeout = '10s'")
                await cur.execute(cleaned)

                if cur.description is None:
                    return {"success": False, "error": "Query returned no results."}

                col_names = [desc[0] for desc in cur.description]
                rows_raw = await cur.fetchmany(500)

                rows = [
                    {col: _serialize_value(val) for col, val in zip(col_names, row)}
                    for row in rows_raw
                ]

                return {
                    "success": True,
                    "row_count": len(rows),
                    "columns": col_names,
                    "rows": rows,
                }
    except Exception as e:
        logger.exception("Error executing query")
        return {"success": False, "error": str(e)}


_VALID_DISPLAY_TYPES = frozenset(
    {"text", "table", "bar_chart", "line_chart", "pie_chart", "scatter_plot"}
)


@tool
async def present_results(
    type: str,
    title: str = "",
    x_axis: str = "",
    y_axis: str = "",
    label_key: str = "",
    value_key: str = "",
) -> dict[str, Any]:
    """Present query results with a visualization. Call this AFTER execute_query
    to tell the frontend how to display the data. Do NOT include the data array —
    the backend attaches it automatically from the last query result.

    Args:
        type: Visualization type. One of: text, table, bar_chart, line_chart,
              pie_chart, scatter_plot.
        title: Chart title (required for charts, optional for text/table).
        x_axis: Column name for the x-axis (bar_chart, line_chart, scatter_plot).
        y_axis: Column name for the y-axis (bar_chart, line_chart, scatter_plot).
        label_key: Column name for labels (pie_chart).
        value_key: Column name for values (pie_chart).
    """
    if type not in _VALID_DISPLAY_TYPES:
        return {
            "success": False,
            "error": f"Invalid display type '{type}'. "
            f"Must be one of: {', '.join(sorted(_VALID_DISPLAY_TYPES))}",
        }

    meta: dict[str, Any] = {"type": type}
    if title:
        meta["title"] = title
    if x_axis:
        meta["x_axis"] = x_axis
    if y_axis:
        meta["y_axis"] = y_axis
    if label_key:
        meta["label_key"] = label_key
    if value_key:
        meta["value_key"] = value_key

    return {"success": True, "display": meta}
