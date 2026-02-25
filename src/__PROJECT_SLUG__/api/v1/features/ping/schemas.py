from pydantic import BaseModel


class PingResponse(BaseModel):
    message: str = "pong"

    model_config = {"json_schema_extra": {"example": {"message": "pong"}}}
