from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class TerritoryCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)


class DistrictCreate(TerritoryCreate):
    division_id: str = Field(min_length=1, max_length=36)


class TerritoryRead(TerritoryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str


class DistrictRead(TerritoryRead):
    division_id: str


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


class ChannelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    object_id: int | None
    engineering_system_type: str | None
    sensor_type: str | None
    engineering_system_tag: str | None
    sensor_name: str | None


Item = TypeVar("Item")


class Page(BaseModel, Generic[Item]):
    items: list[Item]
    total: int
    page: int
    page_size: int
