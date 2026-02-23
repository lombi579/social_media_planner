from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

STATUS_COLUMNS = ("draft", "planned", "published", "failed")
VALID_STATUSES = set(STATUS_COLUMNS)
VALID_PLATFORMS = {"youtube", "instagram", "tiktok", "telegram"}
VALID_ROLES = {"owner", "admin", "editor", "viewer"}
VALID_JOB_STATUSES = {"queued", "processing", "done", "failed", "dead_letter"}


@dataclass(slots=True)
class User:
    id: int
    username: str
    password_hash: str
    created_at: str


@dataclass(slots=True)
class Post:
    id: int
    user_id: int
    workspace_id: int
    title: str
    platform: str
    channel_name: str
    publish_at: str
    status: str
    description: str
    hashtags: str
    media_url: str
    created_at: str


@dataclass(slots=True)
class SocialAccount:
    id: int
    user_id: int
    workspace_id: int
    platform: str
    account_label: str
    access_token: str
    refresh_token: str
    expires_at: str
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
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workspaces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memberships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    workspace_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(user_id, workspace_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    price_monthly INTEGER NOT NULL,
                    post_limit INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace_id INTEGER NOT NULL,
                    plan_code TEXT NOT NULL,
                    status TEXT NOT NULL,
                    renew_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS social_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    workspace_id INTEGER NOT NULL,
                    platform TEXT NOT NULL,
                    account_label TEXT NOT NULL,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS webhooks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    target_url TEXT NOT NULL,
                    secret TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS publish_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace_id INTEGER NOT NULL,
                    post_id INTEGER NOT NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 5,
                    status TEXT NOT NULL,
                    next_run_at TEXT NOT NULL,
                    last_error TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dead_letters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace_id INTEGER NOT NULL,
                    job_id INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    workspace_id INTEGER NOT NULL DEFAULT 1,
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
            self._migrate_posts_columns(conn)
            self._seed_default_plans(conn)
            conn.commit()

    def _migrate_posts_columns(self, conn: sqlite3.Connection) -> None:
        cols = conn.execute("PRAGMA table_info(posts)").fetchall()
        names = {row[1] for row in cols}
        if "user_id" not in names:
            conn.execute("ALTER TABLE posts ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
        if "workspace_id" not in names:
            conn.execute("ALTER TABLE posts ADD COLUMN workspace_id INTEGER NOT NULL DEFAULT 1")

    def _seed_default_plans(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute("SELECT COUNT(*) AS c FROM plans").fetchone()
        if rows["c"] == 0:
            conn.executemany(
                "INSERT INTO plans(code, price_monthly, post_limit) VALUES (?, ?, ?)",
                [("starter", 1900, 200), ("pro", 5900, 2000), ("business", 14900, 10000)],
            )

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat(timespec="seconds")

    @staticmethod
    def _hash_password(password: str) -> str:
        salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
        return f"{salt.hex()}:{dk.hex()}"

    @staticmethod
    def _verify_password(password: str, encoded: str) -> bool:
        salt_hex, hash_hex = encoded.split(":", maxsplit=1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        got = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
        return hmac.compare_digest(got, expected)

    def _user_workspace_ids(self, user_id: int) -> list[int]:
        with self._conn() as conn:
            rows = conn.execute("SELECT workspace_id FROM memberships WHERE user_id = ?", (user_id,)).fetchall()
        return [int(r["workspace_id"]) for r in rows]

    def _ensure_workspace_access(self, user_id: int, workspace_id: int) -> None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM memberships WHERE user_id = ? AND workspace_id = ?",
                (user_id, workspace_id),
            ).fetchone()
        if row is None:
            raise PermissionError("workspace access denied")

    def _log_audit(self, workspace_id: int, user_id: int, action: str, entity_type: str, entity_id: str, payload: dict) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO audit_events(workspace_id, user_id, action, entity_type, entity_id, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (workspace_id, user_id, action, entity_type, str(entity_id), json.dumps(payload), self._now()),
            )
            conn.commit()

    def create_user(self, username: str, password: str) -> User:
        username = username.strip()
        if len(username) < 3:
            raise ValueError("username must be at least 3 chars")
        if len(password) < 6:
            raise ValueError("password must be at least 6 chars")

        with self._conn() as conn:
            try:
                cur = conn.execute(
                    "INSERT INTO users(username, password_hash, created_at) VALUES (?, ?, ?)",
                    (username, self._hash_password(password), self._now()),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("username already exists") from exc
            user_id = cur.lastrowid
            ws = conn.execute(
                "INSERT INTO workspaces(name, created_at) VALUES (?, ?)",
                (f"{username}-workspace", self._now()),
            )
            workspace_id = ws.lastrowid
            conn.execute(
                "INSERT INTO memberships(user_id, workspace_id, role, created_at) VALUES (?, ?, 'owner', ?)",
                (user_id, workspace_id, self._now()),
            )
            conn.execute(
                "INSERT INTO subscriptions(workspace_id, plan_code, status, renew_at, created_at) VALUES (?, 'starter', 'active', ?, ?)",
                (workspace_id, self._now(), self._now()),
            )
            conn.commit()
        return self.get_user(user_id)

    def create_workspace(self, user_id: int, name: str) -> int:
        with self._conn() as conn:
            cur = conn.execute("INSERT INTO workspaces(name, created_at) VALUES (?, ?)", (name.strip(), self._now()))
            workspace_id = cur.lastrowid
            conn.execute(
                "INSERT INTO memberships(user_id, workspace_id, role, created_at) VALUES (?, ?, 'owner', ?)",
                (user_id, workspace_id, self._now()),
            )
            conn.execute(
                "INSERT INTO subscriptions(workspace_id, plan_code, status, renew_at, created_at) VALUES (?, 'starter', 'active', ?, ?)",
                (workspace_id, self._now(), self._now()),
            )
            conn.commit()
        self._log_audit(workspace_id, user_id, "workspace.create", "workspace", str(workspace_id), {"name": name})
        return int(workspace_id)

    def list_workspaces(self, user_id: int) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT w.id, w.name, m.role
                FROM workspaces w
                JOIN memberships m ON m.workspace_id = w.id
                WHERE m.user_id = ?
                ORDER BY w.id
                """,
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def add_member(self, actor_user_id: int, workspace_id: int, username: str, role: str) -> None:
        role = role.strip().lower()
        if role not in VALID_ROLES:
            raise ValueError("invalid role")
        self._ensure_workspace_access(actor_user_id, workspace_id)
        target = self.get_user_by_username(username)
        if target is None:
            raise ValueError("user not found")
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO memberships(user_id, workspace_id, role, created_at) VALUES (?, ?, ?, ?)",
                (target.id, workspace_id, role, self._now()),
            )
            conn.commit()
        self._log_audit(workspace_id, actor_user_id, "member.add", "membership", f"{target.id}:{workspace_id}", {"role": role})

    def set_subscription_plan(self, actor_user_id: int, workspace_id: int, plan_code: str) -> None:
        self._ensure_workspace_access(actor_user_id, workspace_id)
        with self._conn() as conn:
            exists = conn.execute("SELECT 1 FROM plans WHERE code = ?", (plan_code,)).fetchone()
            if exists is None:
                raise ValueError("unknown plan")
            conn.execute(
                "UPDATE subscriptions SET plan_code = ?, renew_at = ? WHERE workspace_id = ?",
                (plan_code, self._now(), workspace_id),
            )
            conn.commit()
        self._log_audit(workspace_id, actor_user_id, "subscription.update", "subscription", str(workspace_id), {"plan": plan_code})

    def get_user(self, user_id: int) -> User:
        with self._conn() as conn:
            row = conn.execute("SELECT id, username, password_hash, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise KeyError(user_id)
        return User(**dict(row))

    def get_user_by_username(self, username: str) -> User | None:
        with self._conn() as conn:
            row = conn.execute("SELECT id, username, password_hash, created_at FROM users WHERE username = ?", (username.strip(),)).fetchone()
        return User(**dict(row)) if row else None

    def authenticate(self, username: str, password: str) -> User | None:
        user = self.get_user_by_username(username)
        if user and self._verify_password(password, user.password_hash):
            return user
        return None

    def add_social_account(
        self,
        user_id: int,
        workspace_id: int,
        *,
        platform: str,
        account_label: str,
        access_token: str,
        refresh_token: str,
        expires_at: str,
    ) -> SocialAccount:
        self._ensure_workspace_access(user_id, workspace_id)
        platform = platform.strip().lower()
        if platform not in VALID_PLATFORMS:
            raise ValueError("invalid platform")
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO social_accounts(user_id, workspace_id, platform, account_label, access_token, refresh_token, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, workspace_id, platform, account_label.strip(), access_token.strip(), refresh_token.strip(), expires_at.strip(), self._now()),
            )
            conn.commit()
            account_id = cur.lastrowid
            row = conn.execute(
                "SELECT id, user_id, workspace_id, platform, account_label, access_token, refresh_token, expires_at, created_at FROM social_accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
        self._log_audit(workspace_id, user_id, "oauth.connect", "social_account", str(account_id), {"platform": platform})
        return SocialAccount(**dict(row))

    def list_social_accounts(self, user_id: int, workspace_id: int) -> list[SocialAccount]:
        self._ensure_workspace_access(user_id, workspace_id)
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, user_id, workspace_id, platform, account_label, access_token, refresh_token, expires_at, created_at FROM social_accounts WHERE workspace_id = ? ORDER BY id",
                (workspace_id,),
            ).fetchall()
        return [SocialAccount(**dict(r)) for r in rows]

    def list_posts(self, user_id: int, workspace_id: int, *, status: str | None = None, platform: str | None = None, q: str | None = None) -> list[Post]:
        self._ensure_workspace_access(user_id, workspace_id)
        clauses: list[str] = ["workspace_id = ?", "user_id = ?"]
        params: list[str | int] = [workspace_id, user_id]
        if status and status.strip().lower() in VALID_STATUSES:
            clauses.append("status = ?")
            params.append(status.strip().lower())
        if platform and platform.strip().lower() in VALID_PLATFORMS:
            clauses.append("platform = ?")
            params.append(platform.strip().lower())
        if q:
            needle = f"%{q.strip().lower()}%"
            clauses.append("(lower(title) LIKE ? OR lower(description) LIKE ? OR lower(channel_name) LIKE ?)")
            params.extend([needle, needle, needle])
        sql = (
            "SELECT id, user_id, workspace_id, title, platform, channel_name, publish_at, status, description, hashtags, media_url, created_at "
            f"FROM posts WHERE {' AND '.join(clauses)} ORDER BY publish_at"
        )
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [Post(**dict(r)) for r in rows]

    def create_post(self, user_id: int, workspace_id: int, *, title: str, platform: str, channel_name: str, publish_at: str, status: str, description: str, hashtags: str, media_url: str) -> Post:
        self._ensure_workspace_access(user_id, workspace_id)
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
                INSERT INTO posts(user_id, workspace_id, title, platform, channel_name, publish_at, status, description, hashtags, media_url, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, workspace_id, title.strip(), platform, channel_name.strip(), publish_at.strip(), status, description.strip(), hashtags.strip(), media_url.strip(), self._now()),
            )
            post_id = cur.lastrowid
            conn.commit()
            row = conn.execute(
                "SELECT id, user_id, workspace_id, title, platform, channel_name, publish_at, status, description, hashtags, media_url, created_at FROM posts WHERE id = ?",
                (post_id,),
            ).fetchone()
        self.enqueue_publish_job(user_id, workspace_id, int(post_id), publish_at.strip())
        self._log_audit(workspace_id, user_id, "post.create", "post", str(post_id), {"platform": platform})
        return Post(**dict(row))

    def update_post(self, user_id: int, workspace_id: int, post_id: int, *, title: str, platform: str, channel_name: str, publish_at: str, description: str, hashtags: str, media_url: str) -> Post:
        self._ensure_workspace_access(user_id, workspace_id)
        platform = platform.strip().lower()
        if platform not in VALID_PLATFORMS:
            raise ValueError("invalid platform")
        datetime.strptime(publish_at, "%Y-%m-%d %H:%M")
        with self._conn() as conn:
            cur = conn.execute(
                """
                UPDATE posts
                SET title = ?, platform = ?, channel_name = ?, publish_at = ?, description = ?, hashtags = ?, media_url = ?
                WHERE id = ? AND workspace_id = ? AND user_id = ?
                """,
                (title.strip(), platform, channel_name.strip(), publish_at.strip(), description.strip(), hashtags.strip(), media_url.strip(), post_id, workspace_id, user_id),
            )
            conn.commit()
            if cur.rowcount == 0:
                raise KeyError(post_id)
            row = conn.execute(
                "SELECT id, user_id, workspace_id, title, platform, channel_name, publish_at, status, description, hashtags, media_url, created_at FROM posts WHERE id = ?",
                (post_id,),
            ).fetchone()
        self._log_audit(workspace_id, user_id, "post.update", "post", str(post_id), {"platform": platform})
        return Post(**dict(row))

    def update_status(self, user_id: int, workspace_id: int, post_id: int, status: str) -> Post:
        self._ensure_workspace_access(user_id, workspace_id)
        status = status.strip().lower()
        if status not in VALID_STATUSES:
            raise ValueError("invalid status")
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE posts SET status = ? WHERE id = ? AND workspace_id = ? AND user_id = ?",
                (status, post_id, workspace_id, user_id),
            )
            conn.commit()
            if cur.rowcount == 0:
                raise KeyError(post_id)
            row = conn.execute(
                "SELECT id, user_id, workspace_id, title, platform, channel_name, publish_at, status, description, hashtags, media_url, created_at FROM posts WHERE id = ?",
                (post_id,),
            ).fetchone()
        self._log_audit(workspace_id, user_id, "post.status", "post", str(post_id), {"status": status})
        return Post(**dict(row))

    def delete_post(self, user_id: int, workspace_id: int, post_id: int) -> None:
        self._ensure_workspace_access(user_id, workspace_id)
        with self._conn() as conn:
            conn.execute("DELETE FROM posts WHERE id = ? AND workspace_id = ? AND user_id = ?", (post_id, workspace_id, user_id))
            conn.commit()
        self._log_audit(workspace_id, user_id, "post.delete", "post", str(post_id), {})

    def enqueue_publish_job(self, user_id: int, workspace_id: int, post_id: int, next_run_at: str) -> None:
        self._ensure_workspace_access(user_id, workspace_id)
        datetime.strptime(next_run_at, "%Y-%m-%d %H:%M")
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO publish_jobs(workspace_id, post_id, status, next_run_at, created_at, updated_at)
                VALUES (?, ?, 'queued', ?, ?, ?)
                """,
                (workspace_id, post_id, next_run_at, self._now(), self._now()),
            )
            conn.commit()

    def process_due_jobs(self, limit: int = 20) -> dict[str, int]:
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        processed = failed = dead = 0
        with self._conn() as conn:
            jobs = conn.execute(
                """
                SELECT id, workspace_id, post_id, attempt_count, max_attempts
                FROM publish_jobs
                WHERE status IN ('queued', 'failed') AND next_run_at <= ?
                ORDER BY id
                LIMIT ?
                """,
                (now, limit),
            ).fetchall()

            for job in jobs:
                attempt = int(job["attempt_count"]) + 1
                conn.execute(
                    "UPDATE publish_jobs SET status = 'processing', attempt_count = ?, updated_at = ? WHERE id = ?",
                    (attempt, self._now(), int(job["id"])),
                )
                post = conn.execute("SELECT id, status FROM posts WHERE id = ?", (int(job["post_id"]),)).fetchone()
                if post is None:
                    err = "post not found"
                else:
                    # Stub publisher for MVP: treat as published.
                    err = ""

                if not err:
                    conn.execute(
                        "UPDATE posts SET status = 'published' WHERE id = ?",
                        (int(job["post_id"]),),
                    )
                    conn.execute(
                        "UPDATE publish_jobs SET status = 'done', last_error = '', updated_at = ? WHERE id = ?",
                        (self._now(), int(job["id"])),
                    )
                    conn.execute(
                        "INSERT INTO notifications(user_id, kind, payload_json, created_at) VALUES (?, 'post_published', ?, ?)",
                        (1, json.dumps({"post_id": int(job["post_id"])}), self._now()),
                    )
                    processed += 1
                    continue

                if attempt >= int(job["max_attempts"]):
                    conn.execute(
                        "UPDATE publish_jobs SET status = 'dead_letter', last_error = ?, updated_at = ? WHERE id = ?",
                        (err, self._now(), int(job["id"])),
                    )
                    conn.execute(
                        "INSERT INTO dead_letters(workspace_id, job_id, reason, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
                        (int(job["workspace_id"]), int(job["id"]), err, json.dumps({"post_id": int(job["post_id"])}), self._now()),
                    )
                    dead += 1
                else:
                    conn.execute(
                        "UPDATE publish_jobs SET status = 'failed', last_error = ?, updated_at = ? WHERE id = ?",
                        (err, self._now(), int(job["id"])),
                    )
                    failed += 1
            conn.commit()
        return {"processed": processed, "failed": failed, "dead_letter": dead}

    def list_audit_events(self, user_id: int, workspace_id: int, limit: int = 100) -> list[dict]:
        self._ensure_workspace_access(user_id, workspace_id)
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, action, entity_type, entity_id, payload_json, created_at FROM audit_events WHERE workspace_id = ? ORDER BY id DESC LIMIT ?",
                (workspace_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_notifications(self, user_id: int, limit: int = 100) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, kind, payload_json, created_at FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def create_webhook(self, user_id: int, workspace_id: int, event_type: str, target_url: str, secret: str) -> int:
        self._ensure_workspace_access(user_id, workspace_id)
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO webhooks(workspace_id, event_type, target_url, secret, active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
                (workspace_id, event_type.strip(), target_url.strip(), secret.strip(), self._now()),
            )
            conn.commit()
            webhook_id = cur.lastrowid
        self._log_audit(workspace_id, user_id, "webhook.create", "webhook", str(webhook_id), {"event_type": event_type})
        return int(webhook_id)

    def list_webhooks(self, user_id: int, workspace_id: int) -> list[dict]:
        self._ensure_workspace_access(user_id, workspace_id)
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, event_type, target_url, active, created_at FROM webhooks WHERE workspace_id = ? ORDER BY id DESC",
                (workspace_id,),
            ).fetchall()
        return [dict(r) for r in rows]
