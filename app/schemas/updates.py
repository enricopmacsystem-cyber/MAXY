from pydantic import BaseModel


class UpdateCheckRequest(BaseModel):
    current_version: str


class UpdateCheckResponse(BaseModel):
    update_available: bool
    latest_version: str
    download_url: str | None = None
    release_notes: str | None = None
    mandatory: bool = False
