from __future__ import annotations

import os

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from web.repository import Repository, VALID_PLATFORMS, VALID_STATUSES

app = FastAPI(title="Buffer-style Social Planner")
repo = Repository(os.getenv("DATABASE_FILE", "data/app.db"))
templates = Jinja2Templates(directory="web/templates")
app.mount("/static", StaticFiles(directory="web/static"), name="static")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def board(request: Request) -> HTMLResponse:
    posts = repo.list_posts()
    by_status = {status: [p for p in posts if p.status == status] for status in VALID_STATUSES}
    return templates.TemplateResponse(
        "board.html",
        {
            "request": request,
            "columns": ["draft", "planned", "published", "failed"],
            "by_status": by_status,
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
