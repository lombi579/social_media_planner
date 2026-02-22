from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum


class Platform(StrEnum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"


class ScheduleStatus(StrEnum):
    PLANNED = "planned"
    PUBLISHED = "published"
    FAILED = "failed"


@dataclass(slots=True)
class UploadRequest:
    id: str
    user_id: int
    platform: Platform
    account: str
    publish_at: datetime
    description: str
    hashtags: str | None = None
    status: ScheduleStatus = ScheduleStatus.PLANNED
    error: str | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["platform"] = self.platform.value
        data["status"] = self.status.value
        data["publish_at"] = self.publish_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, raw: dict) -> "UploadRequest":
        return cls(
            id=str(raw["id"]),
            user_id=int(raw["user_id"]),
            platform=Platform(raw["platform"]),
            account=str(raw["account"]),
            publish_at=datetime.fromisoformat(raw["publish_at"]),
            description=str(raw["description"]),
            hashtags=raw.get("hashtags") or None,
            status=ScheduleStatus(raw.get("status", ScheduleStatus.PLANNED.value)),
            error=raw.get("error") or None,
        )
