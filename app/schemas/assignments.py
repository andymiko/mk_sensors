from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class AssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    object_id: int
    channel_id: int | None = None
    technician_id: str
    scheduled_date: date


class AssignmentSensor(BaseModel):
    id: int
    name: str | None
    type: str | None
    status: str
    completed_at: datetime | None


class AssignmentRead(BaseModel):
    id: str
    object_id: int
    object_name: str
    channel_id: int | None
    sensor_name: str | None
    sensor_type: str | None
    sensors: list[AssignmentSensor] = Field(default_factory=list)
    technician_id: str
    technician_name: str
    dispatcher_id: str
    dispatcher_name: str
    scheduled_date: date
    status: str
    completed_at: datetime | None
    created_at: int


class TechnicianOption(BaseModel):
    id: str
    name: str
    email: str
