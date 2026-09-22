from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ForecastCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    channel_id: int
    event_at: datetime
    is_alarm: bool
    sensor_value: str | None = Field(default=None, max_length=2000)


class ForecastRead(BaseModel):
    id: str
    event_id: int
    event_at: datetime
    is_alarm: bool
    sensor_value: str | None
    channel_id: int
    sensor_name: str | None
    sensor_type: str | None
    object_id: int
    object_name: str
    model_key: str
    model_version: str
    forecast_at: datetime
    target_from: datetime
    target_until: datetime
    status: str
    risk_score: float | None
    threshold: float | None
    warning: bool | None
    created_at: int


class ForecastChannelOption(BaseModel):
    id: int
    sensor_name: str | None
    sensor_type: str | None
    object_id: int
    object_name: str
    model_key: str
