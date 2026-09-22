from typing import Optional, List

from pydantic import BaseModel, ConfigDict, EmailStr, Field

class RoleModel(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PermissionModel(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserRead(BaseModel):
    id: str
    email: EmailStr
    name: str = Field(max_length=200)
    is_active: bool = False
    roles: List[RoleModel] = Field(default_factory=list)
    role_codes: List[str] = Field(default_factory=list)
    permission_codes: List[str] = Field(default_factory=list)
    permissions: List[PermissionModel] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class UserModel(UserRead):
    pass
