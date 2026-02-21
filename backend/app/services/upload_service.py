import csv
import io
import re
import uuid

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = {"text/csv", "application/octet-stream"}


def sanitize_table_name(filename: str) -> str:
    """Sanitize a filename into a valid PostgreSQL table name component.

    Strips extension, lowercases, replaces non-alphanumeric chars with
    underscores, collapses runs, and strips leading/trailing underscores.
    """
    name = filename.rsplit(".", 1)[0] if "." in filename else filename
    name = name.lower()
    name = re.sub(r"[^a-z0-9]", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")
    return name or "data"


def generate_table_name(session_id: uuid.UUID, filename: str) -> str:
    """Build a collision-safe table name: s_{first8 hex of session}_{sanitized}."""
    prefix = session_id.hex[:8]
    sanitized = sanitize_table_name(filename)
    return f"s_{prefix}_{sanitized}"


def validate_csv_content(content: bytes) -> tuple[list[str], str | None]:
    """Validate that *content* is parseable CSV with headers and at least one row.

    Returns ``(headers, None)`` on success or ``([], error_message)`` on failure.
    """
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return [], "File is not valid UTF-8 text"

    if not text.strip():
        return [], "CSV file is empty"

    reader = csv.reader(io.StringIO(text))

    try:
        headers = next(reader)
    except StopIteration:
        return [], "CSV file has no headers"

    if not headers or all(h.strip() == "" for h in headers):
        return [], "CSV file has no valid headers"

    try:
        next(reader)
    except StopIteration:
        return [], "CSV file has no data rows"

    return headers, None
