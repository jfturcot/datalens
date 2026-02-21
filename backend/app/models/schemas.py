import uuid
from datetime import datetime

from pydantic import BaseModel


class SessionResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    status: str
