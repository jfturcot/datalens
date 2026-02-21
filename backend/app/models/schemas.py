import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class SessionRequest(BaseModel):
    password: str | None = None


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


# --- Conversation schemas ---


class MessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class DisplayData(BaseModel):
    type: Literal[
        "text", "table", "bar_chart", "line_chart", "pie_chart", "scatter_plot"
    ]
    title: str | None = None
    data: list[dict[str, Any]] = []
    x_axis: str | None = None
    y_axis: str | None = None
    label_key: str | None = None
    value_key: str | None = None


class MessageCompleteData(BaseModel):
    content: str
    sql: str | None = None
    display: DisplayData | None = None


class ConversationResponse(BaseModel):
    id: uuid.UUID
    filename: str
    table_name: str
    row_count: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationMessage(BaseModel):
    role: str
    content: str
    sql: str | None = None
    display: DisplayData | None = None


class ConversationDetailResponse(BaseModel):
    id: uuid.UUID
    filename: str
    table_name: str
    row_count: int | None
    created_at: datetime
    messages: list[ConversationMessage]
