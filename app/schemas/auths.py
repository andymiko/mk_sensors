from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    # При входе проверяем любой непустой пароль. Политика длины относится только
    # к регистрации; иначе неверный короткий пароль превращается в 422 вместо 401.
    password: str = Field(min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="Новый сотрудник", min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str

    model_config = {"from_attributes": True}


class AuthModel(BaseModel):
    id: str
    email: str
    password: str
    is_active: bool
