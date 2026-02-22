from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

STATUS_COLUMNS = ("draft", "planned", "published", "failed")
VALID_STATUSES = set(STATUS_COLUMNS)
VALID_PLATFORMS = {"youtube", "instagram", "tiktok", "telegram"}


@dataclass(slots=True)
class Post:
    id: int
    title: str
    platform: str
    channel_name: str
    publish_at: str
    status: str
    description: str
    hashtags: str
    media_url: str
    created_at: str


class Repository:
    def __init__(self, db_path: str = "data/app.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    channel_name TEXT NOT NULL,
                    publish_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    description TEXT NOT NULL,
                    hashtags TEXT NOT NULL DEFAULT '',
                    media_url TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def list_posts(self) -> list[Post]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, title, platform, channel_name, publish_at, status, description, hashtags, media_url, created_at "
                "FROM posts ORDER BY publish_at"
            ).fetchall()
        return [Post(**dict(row)) for row in rows]

    def create_post(
        self,
        title: str,
        platform: str,
        channel_name: str,
        publish_at: str,
        status: str,
        description: str,
        hashtags: str,
        media_url: str,
    ) -> Post:
        platform = platform.strip().lower()
        status = status.strip().lower()
        if platform not in VALID_PLATFORMS:
            raise ValueError("invalid platform")
        if status not in VALID_STATUSES:
            raise ValueError("invalid status")
        datetime.strptime(publish_at, "%Y-%m-%d %H:%M")

        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO posts(title, platform, channel_name, publish_at, status, description, hashtags, media_url, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title.strip(),
                    platform,
                    channel_name.strip(),
                    publish_at.strip(),
                    status,
                    description.strip(),
                    hashtags.strip(),
                    media_url.strip(),
                    datetime.utcnow().isoformat(timespec="seconds"),
                ),
            )
            conn.commit()
            post_id = cur.lastrowid
        return self.get_post(post_id)

    def get_post(self, post_id: int) -> Post:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id, title, platform, channel_name, publish_at, status, description, hashtags, media_url, created_at "
                "FROM posts WHERE id = ?",
                (post_id,),
            ).fetchone()
        if row is None:
            raise KeyError(post_id)
        return Post(**dict(row))

    def update_status(self, post_id: int, status: str) -> Post:
        status = status.strip().lower()
        if status not in VALID_STATUSES:
            raise ValueError("invalid status")
        with self._conn() as conn:
            cur = conn.execute("UPDATE posts SET status = ? WHERE id = ?", (status, post_id))
            conn.commit()
            if cur.rowcount == 0:
                raise KeyError(post_id)
        return self.get_post(post_id)

    def delete_post(self, post_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
            conn.commit()
