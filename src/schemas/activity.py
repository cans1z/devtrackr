"""Activity log schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ActivityLogOut(BaseModel):
    """Activity log output schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    activity_type: str
    entity_type: str
    entity_id: int | None
    description: str
    activity_metadata: dict | None = None
    created_at: datetime


class ActivityLogListResponse(BaseModel):
    """Paginated activity log response."""

    items: list[ActivityLogOut]
    next_cursor: str | None = None
    has_next: bool = False
    total_count: int | None = None
