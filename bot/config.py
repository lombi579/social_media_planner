from __future__ import annotations

import json
import os
from dataclasses import dataclass

from dotenv import load_dotenv

from bot.models import Platform

DEFAULT_ACCOUNTS: dict[Platform, list[str]] = {
    Platform.YOUTUBE: ["YouTube_Main", "YouTube_Blog"],
    Platform.INSTAGRAM: ["Instagram_Main", "Instagram_Brand"],
    Platform.TIKTOK: ["TikTok_Main", "TikTok_Trend"],
}


@dataclass(slots=True)
class Settings:
    bot_token: str
    accounts: dict[Platform, list[str]]
    schedules_file: str


def _parse_accounts(raw: str | None) -> dict[Platform, list[str]]:
    if not raw:
        return DEFAULT_ACCOUNTS

    loaded = json.loads(raw)
    parsed: dict[Platform, list[str]] = {}
    for platform in Platform:
        values = loaded.get(platform.value, DEFAULT_ACCOUNTS[platform])
        parsed[platform] = [str(v) for v in values]
    return parsed


def load_settings() -> Settings:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is required. Add it to .env or environment variables.")

    accounts = _parse_accounts(os.getenv("ACCOUNTS_JSON"))
    schedules_file = os.getenv("SCHEDULES_FILE", "data/schedules.json")
    return Settings(bot_token=token, accounts=accounts, schedules_file=schedules_file)
