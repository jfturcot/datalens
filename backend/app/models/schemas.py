import uuid
from datetime import datetime

from pydantic import BaseModel


class SessionResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    status: str


class ColumnInfo(BaseModel):
    name: str
    type: str


class UploadResponse(BaseModel):
    conversation_id: uuid.UUID
    filename: str
    table_name: str
    row_count: int
    columns: list[ColumnInfo]
