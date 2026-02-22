from __future__ import annotations

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from web.repository import BoardRepository

app = FastAPI(title="Social Media Planner Board")
repo = BoardRepository()
templates = Jinja2Templates(directory="web/templates")
app.mount("/static", StaticFiles(directory="web/static"), name="static")


@app.get("/", response_class=HTMLResponse)
def board(request: Request) -> HTMLResponse:
    items = repo.list_items()
    return templates.TemplateResponse("board.html", {"request": request, "items": items})


@app.post("/items")
def create_item(
    platform: str = Form(...),
    account: str = Form(...),
    publish_at: str = Form(...),
    description: str = Form(...),
    hashtags: str = Form(""),
) -> RedirectResponse:
    try:
        repo.create_item(
            platform=platform.strip().lower(),
            account=account.strip(),
            publish_at=publish_at.strip(),
            description=description.strip(),
            hashtags=hashtags.strip(),
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="publish_at must be YYYY-MM-DD HH:MM")
    return RedirectResponse(url="/", status_code=303)


@app.post("/items/{item_id}/status")
def update_status(item_id: int, status: str = Form(...)) -> RedirectResponse:
    try:
        repo.update_status(item_id, status)
    except KeyError:
        raise HTTPException(status_code=404, detail="Item not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return RedirectResponse(url="/", status_code=303)


@app.post("/items/{item_id}/delete")
def delete_item(item_id: int) -> RedirectResponse:
    repo.delete_item(item_id)
    return RedirectResponse(url="/", status_code=303)
