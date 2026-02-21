import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_session
from app.models import get_db
from app.models.conversation import Conversation
from app.models.schemas import ColumnInfo, UploadResponse
from app.models.session import Session
from app.services.minio_service import upload_file
from app.services.upload_service import (
    ALLOWED_CONTENT_TYPES,
    MAX_FILE_SIZE,
    generate_table_name,
    validate_csv_content,
)

router = APIRouter()

SHARED_TMP = "/tmp/datalens"


@router.post("/upload", response_model=UploadResponse)
async def upload_csv(
    file: UploadFile,
    session: Annotated[Session, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UploadResponse:
    """Upload a CSV file, store in MinIO, ingest into PostgreSQL via pg_duckdb."""
    # --- Validate file metadata ---
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="File must be a CSV")

    # --- Read and validate size ---
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Maximum file size is 10MB")

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    # --- Validate CSV content ---
    _headers, error = validate_csv_content(content)
    if error:
        raise HTTPException(status_code=400, detail=error)

    # --- Upload to MinIO ---
    session_id_str = str(session.id)
    await upload_file(session_id_str, file.filename, content)

    # --- Save temp file for pg_duckdb ingestion ---
    # Use a UUID temp filename to avoid any path injection
    tmp_dir = os.path.join(SHARED_TMP, session_id_str)
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_filename = f"{uuid.uuid4().hex}.csv"
    tmp_path = os.path.join(tmp_dir, tmp_filename)

    try:
        with open(tmp_path, "wb") as f:
            f.write(content)

        # --- Create table via pg_duckdb ---
        table_name = generate_table_name(session.id, file.filename)

        await db.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
        create_sql = text(
            f"CREATE TABLE {table_name} AS SELECT * FROM read_csv('{tmp_path}')"
        )
        await db.execute(create_sql)

        # --- Get row count ---
        count_result = await db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        row_count = count_result.scalar() or 0

        # --- Get column info ---
        col_result = await db.execute(
            text(
                "SELECT column_name, data_type "
                "FROM information_schema.columns "
                "WHERE table_name = :tbl "
                "ORDER BY ordinal_position"
            ),
            {"tbl": table_name},
        )
        columns = [
            ColumnInfo(name=row[0], type=row[1]) for row in col_result.fetchall()
        ]

        await db.commit()
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # --- Create conversation record ---
    conversation = Conversation(
        id=uuid.uuid4(),
        session_id=session.id,
        filename=file.filename,
        table_name=table_name,
        row_count=row_count,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return UploadResponse(
        conversation_id=conversation.id,
        filename=file.filename,
        table_name=table_name,
        row_count=row_count,
        columns=columns,
    )
