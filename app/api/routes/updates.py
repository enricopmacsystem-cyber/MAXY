from fastapi import APIRouter

from app.api.dependencies import DbSession
from app.schemas.updates import UpdateCheckRequest, UpdateCheckResponse
from app.services.update_service import UpdateService

router = APIRouter()


@router.post("/check", response_model=UpdateCheckResponse)
def check_updates(payload: UpdateCheckRequest, db: DbSession) -> UpdateCheckResponse:
    service = UpdateService(db)
    return service.check_for_update(payload.current_version)
