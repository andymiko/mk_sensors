from pydantic import BaseModel, Field


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserRolesUpdate(BaseModel):
    role_ids: list[str] = Field(default_factory=list)


class UserDivisionsUpdate(BaseModel):
    division_ids: list[str] = Field(default_factory=list, max_length=100)


class RoleCreate(BaseModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_.-]{1,99}$")
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class RoleUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class RolePermissionsUpdate(BaseModel):
    permission_ids: list[str] = Field(default_factory=list)


class PermissionCreate(BaseModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_.-]{1,99}$")
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=500)


class PermissionUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=500)
