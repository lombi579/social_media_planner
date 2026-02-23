from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    app_env: str
    host: str
    port: int
    reload: bool
    database_file: str


def _to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    default_reload = app_env != "production"
    return Settings(
        app_env=app_env,
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8080")),
        reload=_to_bool(os.getenv("APP_RELOAD"), default_reload),
        database_file=os.getenv("DATABASE_FILE", "data/app.db"),
    )
