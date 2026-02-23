from __future__ import annotations

import json
from pathlib import Path

from bot.models import UploadRequest


class ScheduleStorage:
    def __init__(self, path: str = "data/schedules.json") -> None:
        self.path = Path(path)

    def load(self) -> list[UploadRequest]:
        if not self.path.exists():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return [UploadRequest.from_dict(item) for item in payload]

    def save(self, items: list[UploadRequest]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [item.to_dict() for item in items]
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
