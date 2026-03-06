from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None
    refresh_expires_in: int | None = None


class PasswordGrantRequest(BaseModel):
    username: str
    password: str
    scope: str = ""
    grant_type: str | None = None
    client_id: str | None = None
    client_secret: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str
