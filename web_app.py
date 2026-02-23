from __future__ import annotations

from dataclasses import asdict
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen
import json
import secrets
from datetime import datetime

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from web.repository import Repository, STATUS_COLUMNS, VALID_PLATFORMS, VALID_ROLES
from web.settings import load_settings

settings = load_settings()
app = FastAPI(title="Buffer-style Social Planner")
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
repo = Repository(settings.database_file)
templates = Jinja2Templates(directory="web/templates")
app.mount("/static", StaticFiles(directory="web/static"), name="static")


def _current_user(request: Request) -> tuple[int, str] | None:
    user_id = request.session.get("user_id")
    username = request.session.get("username")
    if not user_id or not username:
        return None
    return int(user_id), str(username)


def _require_user(request: Request) -> tuple[int, str]:
    user = _current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="login required")
    return user


def _active_workspace_id(request: Request, user_id: int) -> int:
    current = request.session.get("workspace_id")
    workspaces = repo.list_workspaces(user_id)
    if not workspaces:
        raise HTTPException(status_code=400, detail="no workspace")
    if current:
        ids = {int(w["id"]) for w in workspaces}
        if int(current) in ids:
            return int(current)
    first_id = int(workspaces[0]["id"])
    request.session["workspace_id"] = first_id
    return first_id


def _youtube_oauth_ready() -> bool:
    return bool(settings.youtube_client_id and settings.youtube_client_secret and settings.youtube_redirect_uri)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "env": settings.app_env}


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request) -> HTMLResponse:
    if _current_user(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("register.html", {"request": request, "error": ""})


@app.post("/register", response_class=HTMLResponse)
def register(request: Request, username: str = Form(...), password: str = Form(...)):
    try:
        user = repo.create_user(username, password)
    except ValueError as exc:
        return templates.TemplateResponse("register.html", {"request": request, "error": str(exc)}, status_code=400)

    request.session["user_id"] = user.id
    request.session["username"] = user.username
    ws = repo.list_workspaces(user.id)
    if ws:
        request.session["workspace_id"] = int(ws[0]["id"])
    return RedirectResponse(url="/", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    if _current_user(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": ""})


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = repo.authenticate(username, password)
    if user is None:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный логин или пароль"}, status_code=401)

    request.session["user_id"] = user.id
    request.session["username"] = user.username
    ws = repo.list_workspaces(user.id)
    if ws:
        request.session["workspace_id"] = int(ws[0]["id"])
    return RedirectResponse(url="/", status_code=303)


@app.post("/logout")
def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@app.post("/workspace/select")
def select_workspace(request: Request, workspace_id: int = Form(...)) -> RedirectResponse:
    user_id, _ = _require_user(request)
    ids = {int(w["id"]) for w in repo.list_workspaces(user_id)}
    if workspace_id not in ids:
        raise HTTPException(status_code=403, detail="workspace access denied")
    request.session["workspace_id"] = int(workspace_id)
    return RedirectResponse(url="/", status_code=303)


@app.post("/workspace/create")
def create_workspace(request: Request, name: str = Form(...)) -> RedirectResponse:
    user_id, _ = _require_user(request)
    workspace_id = repo.create_workspace(user_id, name)
    request.session["workspace_id"] = workspace_id
    return RedirectResponse(url="/", status_code=303)


@app.post("/workspace/members")
def add_member(request: Request, username: str = Form(...), role: str = Form("viewer")) -> RedirectResponse:
    user_id, _ = _require_user(request)
    workspace_id = _active_workspace_id(request, user_id)
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="invalid role")
    repo.add_member(user_id, workspace_id, username, role)
    return RedirectResponse(url="/", status_code=303)


@app.post("/workspace/plan")
def update_plan(request: Request, plan_code: str = Form(...)) -> RedirectResponse:
    user_id, _ = _require_user(request)
    workspace_id = _active_workspace_id(request, user_id)
    repo.set_subscription_plan(user_id, workspace_id, plan_code)
    return RedirectResponse(url="/", status_code=303)


@app.post("/workspace/accounts")
def add_social_account(
    request: Request,
    platform: str = Form(...),
    account_label: str = Form(...),
    access_token: str = Form(...),
    refresh_token: str = Form(...),
    expires_at: str = Form(...),
) -> RedirectResponse:
    user_id, _ = _require_user(request)
    workspace_id = _active_workspace_id(request, user_id)
    repo.add_social_account(
        user_id,
        workspace_id,
        platform=platform,
        account_label=account_label,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )
    return RedirectResponse(url="/", status_code=303)


@app.get("/oauth/youtube/start")
def oauth_youtube_start(request: Request) -> RedirectResponse:
    user_id, _ = _require_user(request)
    workspace_id = _active_workspace_id(request, user_id)
    if not _youtube_oauth_ready():
        raise HTTPException(status_code=500, detail="YouTube OAuth env is not configured")

    state = secrets.token_urlsafe(24)
    repo.create_oauth_state(user_id, workspace_id, "youtube", state)
    params = {
        "client_id": settings.youtube_client_id,
        "redirect_uri": settings.youtube_redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/youtube.upload",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(url=auth_url, status_code=303)


@app.get("/oauth/youtube/callback")
def oauth_youtube_callback(request: Request, code: str | None = Query(default=None), state: str | None = Query(default=None)) -> RedirectResponse:
    user_id, _ = _require_user(request)
    workspace_id = _active_workspace_id(request, user_id)
    if not code or not state:
        raise HTTPException(status_code=400, detail="missing oauth code/state")
    if not repo.consume_oauth_state(user_id, workspace_id, "youtube", state):
        raise HTTPException(status_code=400, detail="invalid oauth state")
    if not _youtube_oauth_ready():
        raise HTTPException(status_code=500, detail="YouTube OAuth env is not configured")

    token_req = UrlRequest(
        "https://oauth2.googleapis.com/token",
        data=urlencode(
            {
                "code": code,
                "client_id": settings.youtube_client_id,
                "client_secret": settings.youtube_client_secret,
                "redirect_uri": settings.youtube_redirect_uri,
                "grant_type": "authorization_code",
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(token_req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"oauth token exchange failed: {exc}")

    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    expires_in = int(payload.get("expires_in", 3600))
    if not access_token:
        raise HTTPException(status_code=502, detail="oauth token exchange returned empty access_token")

    expires_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    repo.add_social_account(
        user_id,
        workspace_id,
        platform="youtube",
        account_label="YouTube OAuth",
        access_token=access_token,
        refresh_token=refresh_token or "",
        expires_at=expires_at,
    )
    return RedirectResponse(url="/", status_code=303)


@app.get("/api/posts")
def api_posts(
    request: Request,
    status: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> list[dict]:
    user_id, _ = _require_user(request)
    workspace_id = _active_workspace_id(request, user_id)
    return [asdict(post) for post in repo.list_posts(user_id, workspace_id, status=status, platform=platform, q=q)]


@app.post("/api/worker/run")
def run_worker(request: Request, limit: int = Form(20)) -> dict:
    _require_user(request)
    return repo.process_due_jobs(limit=max(1, min(limit, 500)))


@app.get("/api/audit")
def api_audit(request: Request, limit: int = Query(default=100)) -> list[dict]:
    user_id, _ = _require_user(request)
    workspace_id = _active_workspace_id(request, user_id)
    return repo.list_audit_events(user_id, workspace_id, limit=max(1, min(limit, 500)))


@app.get("/api/notifications")
def api_notifications(request: Request, limit: int = Query(default=100)) -> list[dict]:
    user_id, _ = _require_user(request)
    return repo.list_notifications(user_id, limit=max(1, min(limit, 500)))


@app.get("/api/webhooks")
def api_webhooks(request: Request) -> list[dict]:
    user_id, _ = _require_user(request)
    workspace_id = _active_workspace_id(request, user_id)
    return repo.list_webhooks(user_id, workspace_id)


@app.post("/workspace/webhooks")
def create_webhook(
    request: Request,
    event_type: str = Form(...),
    target_url: str = Form(...),
    secret: str = Form(...),
) -> RedirectResponse:
    user_id, _ = _require_user(request)
    workspace_id = _active_workspace_id(request, user_id)
    repo.create_webhook(user_id, workspace_id, event_type, target_url, secret)
    return RedirectResponse(url="/", status_code=303)


@app.get("/", response_class=HTMLResponse)
def board(
    request: Request,
    status: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> HTMLResponse:
    user = _current_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    user_id, username = user
    workspace_id = _active_workspace_id(request, user_id)
    posts = repo.list_posts(user_id, workspace_id, status=status, platform=platform, q=q)
    by_status = {status_key: [p for p in posts if p.status == status_key] for status_key in STATUS_COLUMNS}
    stats = {status_key: len(by_status[status_key]) for status_key in STATUS_COLUMNS}
    workspaces = repo.list_workspaces(user_id)
    accounts = repo.list_social_accounts(user_id, workspace_id)

    return templates.TemplateResponse(
        "board.html",
        {
            "request": request,
            "columns": list(STATUS_COLUMNS),
            "by_status": by_status,
            "stats": stats,
            "filters": {"status": status or "", "platform": platform or "", "q": q or ""},
            "platforms": sorted(VALID_PLATFORMS),
            "current_user": username,
            "workspace_id": workspace_id,
            "workspaces": workspaces,
            "social_accounts": accounts,
            "youtube_oauth_ready": _youtube_oauth_ready(),
        },
    )


@app.post("/posts")
def create_post(
    request: Request,
    title: str = Form(...),
    platform: str = Form(...),
    channel_name: str = Form(...),
    publish_at: str = Form(...),
    status: str = Form("planned"),
    description: str = Form(...),
    hashtags: str = Form(""),
    media_url: str = Form(""),
) -> RedirectResponse:
    user_id, _ = _require_user(request)
    workspace_id = _active_workspace_id(request, user_id)
    if platform not in VALID_PLATFORMS:
        raise HTTPException(status_code=400, detail="invalid platform")
    repo.create_post(
        user_id,
        workspace_id,
        title=title,
        platform=platform,
        channel_name=channel_name,
        publish_at=publish_at,
        status=status,
        description=description,
        hashtags=hashtags,
        media_url=media_url,
    )
    return RedirectResponse(url="/", status_code=303)


@app.post("/posts/{post_id}/edit")
def edit_post(
    request: Request,
    post_id: int,
    title: str = Form(...),
    platform: str = Form(...),
    channel_name: str = Form(...),
    publish_at: str = Form(...),
    description: str = Form(...),
    hashtags: str = Form(""),
    media_url: str = Form(""),
) -> RedirectResponse:
    user_id, _ = _require_user(request)
    workspace_id = _active_workspace_id(request, user_id)
    repo.update_post(
        user_id,
        workspace_id,
        post_id,
        title=title,
        platform=platform,
        channel_name=channel_name,
        publish_at=publish_at,
        description=description,
        hashtags=hashtags,
        media_url=media_url,
    )
    return RedirectResponse(url="/", status_code=303)


@app.post("/posts/{post_id}/status")
def change_status(request: Request, post_id: int, status: str = Form(...)) -> RedirectResponse:
    user_id, _ = _require_user(request)
    workspace_id = _active_workspace_id(request, user_id)
    repo.update_status(user_id, workspace_id, post_id, status)
    return RedirectResponse(url="/", status_code=303)


@app.post("/posts/{post_id}/delete")
def remove_post(request: Request, post_id: int) -> RedirectResponse:
    user_id, _ = _require_user(request)
    workspace_id = _active_workspace_id(request, user_id)
    repo.delete_post(user_id, workspace_id, post_id)
    return RedirectResponse(url="/", status_code=303)
