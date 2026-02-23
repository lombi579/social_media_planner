import uvicorn

from web.settings import load_settings


if __name__ == "__main__":
    settings = load_settings()
    uvicorn.run(
        "web_app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )
