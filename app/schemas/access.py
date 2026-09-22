from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class TerritoryCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)


class DistrictCreate(TerritoryCreate):
    # division_id remains accepted while clients migrate to the many-to-many field.
    division_id: str | None = Field(default=None, min_length=1, max_length=36)
    division_ids: list[str] = Field(default_factory=list, max_length=100)


class TerritoryRead(TerritoryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str


class DistrictRead(TerritoryRead):
    division_id: str
    division_ids: list[str]


class RoleScope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    division_ids: list[str] = Field(default_factory=list, max_length=1000)
    district_ids: list[str] = Field(default_factory=list, max_length=1000)
    object_ids: list[int] = Field(default_factory=list, max_length=10000)


class ObjectDistrictUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    district_id: str | None = Field(max_length=36)


class ObjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    hierarchy_level: int
    parent_id: int | None
    district_id: str | None
    object_type: str
    dispatch_name: str
    longitude: float | None
    latitude: float | None
    district_name: str | None = None


class ObjectUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    dispatch_name: str = Field(min_length=1, max_length=1000)
    object_type: str = Field(min_length=1, max_length=100)
    hierarchy_level: int
    district_id: str | None = Field(default=None, max_length=36)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    latitude: float | None = Field(default=None, ge=-90, le=90)


class ChannelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    object_id: int | None
    engineering_system_type: str | None
    sensor_type: str | None
    engineering_system_tag: str | None
    sensor_name: str | None


class EventRead(BaseModel):
    id: int
    channel_id: int
    object_id: int | None
    event_at: datetime
    is_alarm: bool
    sensor_value: str | None
    sensor_type: str | None
    sensor_name: str | None
    object_name: str | None


class SensorState(BaseModel):
    channel_id: int
    sensor_name: str | None
    sensor_type: str | None
    sensor_value: str | None
    is_alarm: bool | None
    status: str
    event_at: datetime | None


class ObjectDetails(ObjectRead):
    sensors: list[SensorState] = Field(default_factory=list)
    status: str
    status_color: str


class IdsUpdate(BaseModel):
    ids: list[int] = Field(default_factory=list, max_length=10000)


class DivisionMember(BaseModel):
    id: str
    name: str
    email: str


class DivisionDetails(TerritoryRead):
    object_ids: list[int] = Field(default_factory=list)
    users: list[DivisionMember] = Field(default_factory=list)


Item = TypeVar("Item")


class Page(BaseModel, Generic[Item]):
    items: list[Item]
    total: int
    page: int
    page_size: int
