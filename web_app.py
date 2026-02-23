from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from web.repository import Repository, STATUS_COLUMNS, VALID_PLATFORMS
from web.settings import load_settings

settings = load_settings()
app = FastAPI(title="Buffer-style Social Planner")
repo = Repository(settings.database_file)
templates = Jinja2Templates(directory="web/templates")
app.mount("/static", StaticFiles(directory="web/static"), name="static")


@app.get("/health")
def health() -> dict:
    return {"ok": True, "env": settings.app_env}


@app.get("/api/posts")
def api_posts(
    status: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> list[dict]:
    return [asdict(post) for post in repo.list_posts(status=status, platform=platform, q=q)]


@app.get("/", response_class=HTMLResponse)
def board(
    request: Request,
    status: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> HTMLResponse:
    posts = repo.list_posts(status=status, platform=platform, q=q)
    by_status = {status_key: [p for p in posts if p.status == status_key] for status_key in STATUS_COLUMNS}
    stats = {status_key: len(by_status[status_key]) for status_key in STATUS_COLUMNS}
    return templates.TemplateResponse(
        "board.html",
        {
            "request": request,
            "columns": list(STATUS_COLUMNS),
            "by_status": by_status,
            "stats": stats,
            "filters": {"status": status or "", "platform": platform or "", "q": q or ""},
            "platforms": sorted(VALID_PLATFORMS),
        },
    )


@app.post("/posts")
def create_post(
    title: str = Form(...),
    platform: str = Form(...),
    channel_name: str = Form(...),
    publish_at: str = Form(...),
    status: str = Form("planned"),
    description: str = Form(...),
    hashtags: str = Form(""),
    media_url: str = Form(""),
) -> RedirectResponse:
    if platform not in VALID_PLATFORMS:
        raise HTTPException(status_code=400, detail="invalid platform")
    try:
        repo.create_post(
            title=title,
            platform=platform,
            channel_name=channel_name,
            publish_at=publish_at,
            status=status,
            description=description,
            hashtags=hashtags,
            media_url=media_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return RedirectResponse(url="/", status_code=303)


@app.post("/posts/{post_id}/edit")
def edit_post(
    post_id: int,
    title: str = Form(...),
    platform: str = Form(...),
    channel_name: str = Form(...),
    publish_at: str = Form(...),
    description: str = Form(...),
    hashtags: str = Form(""),
    media_url: str = Form(""),
) -> RedirectResponse:
    try:
        repo.update_post(
            post_id,
            title=title,
            platform=platform,
            channel_name=channel_name,
            publish_at=publish_at,
            description=description,
            hashtags=hashtags,
            media_url=media_url,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="post not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return RedirectResponse(url="/", status_code=303)


@app.post("/posts/{post_id}/status")
def change_status(post_id: int, status: str = Form(...)) -> RedirectResponse:
    try:
        repo.update_status(post_id, status)
    except KeyError:
        raise HTTPException(status_code=404, detail="post not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return RedirectResponse(url="/", status_code=303)


@app.post("/posts/{post_id}/delete")
def remove_post(post_id: int) -> RedirectResponse:
    repo.delete_post(post_id)
    return RedirectResponse(url="/", status_code=303)
