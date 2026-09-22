from pydantic import BaseModel, ConfigDict, Field


class FileModel(BaseModel):
    id: str
    user_id: str
    original_name: str
    stored_name: str
    size: int
    content_type: str
    status: str
    created_at: int
    updated_at: int
    model_config = ConfigDict(from_attributes=True)


class FilePage(BaseModel):
    items: list[FileModel] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
