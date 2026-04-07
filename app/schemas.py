import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime


class SiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    created_at: datetime


class CameraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    site_id: uuid.UUID
    name: str
    rtsp_url: str
    status: str
    fps_target: float
    created_at: datetime


class ZoneCreate(BaseModel):
    zone_type: str = "serving"
    geometry: dict = Field(..., description="Polygon or bbox normalized coords, e.g. {type, points}")
    metadata: dict | None = None


class ZoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    camera_id: uuid.UUID
    zone_type: str
    geometry: dict
    meta: dict | None = Field(default=None, serialization_alias="metadata")


class ServingEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    camera_id: uuid.UUID
    plate_track_id: int
    started_at: datetime
    ended_at: datetime | None
    dwell_ms: int | None
    snapshot_uri: str | None
    bbox_snapshot: dict | None
    confidence_avg: float | None


class PlateClassificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    serving_event_id: uuid.UUID
    model_version_id: uuid.UUID | None
    labels: dict
    created_at: datetime


class ServingEventDetailOut(ServingEventOut):
    classifications: list[PlateClassificationOut] = Field(default_factory=list)


class PaginatedEvents(BaseModel):
    items: list[ServingEventOut]
    total: int
    offset: int
    limit: int
