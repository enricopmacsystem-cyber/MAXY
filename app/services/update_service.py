from __future__ import annotations

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.repositories.release_repo import ReleaseRepository
from app.schemas.updates import UpdateCheckResponse


def _parse_version(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in value.strip().split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    return tuple(parts)


class UpdateService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repo = ReleaseRepository(session)

    def check_for_update(self, current_version: str) -> UpdateCheckResponse:
        latest = self.repo.get_latest()
        if not latest:
            return UpdateCheckResponse(
                update_available=False,
                latest_version=current_version,
            )

        update_available = _parse_version(latest.version) > _parse_version(current_version)

        return UpdateCheckResponse(
            update_available=update_available,
            latest_version=latest.version,
            download_url=latest.download_url if update_available else None,
            release_notes=latest.release_notes,
            mandatory=latest.mandatory if update_available else False,
        )
