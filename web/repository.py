from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class BoardItem:
    id: int
    platform: str
    account: str
    publish_at: str
    description: str
    hashtags: str
    status: str


class BoardRepository:
    def __init__(self, db_path: str = "data/board.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS board_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    account TEXT NOT NULL,
                    publish_at TEXT NOT NULL,
                    description TEXT NOT NULL,
                    hashtags TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'planned',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def list_items(self) -> list[BoardItem]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, platform, account, publish_at, description, hashtags, status FROM board_items ORDER BY publish_at"
            ).fetchall()
        return [BoardItem(**dict(r)) for r in rows]

    def create_item(
        self,
        platform: str,
        account: str,
        publish_at: str,
        description: str,
        hashtags: str,
        status: str = "planned",
    ) -> BoardItem:
        datetime.strptime(publish_at, "%Y-%m-%d %H:%M")
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO board_items(platform, account, publish_at, description, hashtags, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (platform, account, publish_at, description, hashtags, status, datetime.utcnow().isoformat()),
            )
            item_id = cur.lastrowid
            conn.commit()
        return self.get_item(item_id)

    def get_item(self, item_id: int) -> BoardItem:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, platform, account, publish_at, description, hashtags, status FROM board_items WHERE id = ?",
                (item_id,),
            ).fetchone()
        if row is None:
            raise KeyError(item_id)
        return BoardItem(**dict(row))

    def update_status(self, item_id: int, status: str) -> BoardItem:
        if status not in {"planned", "published", "failed"}:
            raise ValueError("invalid status")
        with self._connect() as conn:
            conn.execute("UPDATE board_items SET status = ? WHERE id = ?", (status, item_id))
            conn.commit()
        return self.get_item(item_id)

    def delete_item(self, item_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM board_items WHERE id = ?", (item_id,))
            conn.commit()
