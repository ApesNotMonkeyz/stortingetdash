from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
import structlog.stdlib
import uvicorn
from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.PrintLoggerFactory(),
)

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    if settings.database_url:
        from app.db.session import close_db, init_db
        init_db(settings.database_url)
        log.info("db_tilkoblet", url=settings.database_url.split("@")[-1])
    else:
        log.info("db_ikke_konfigurert", backend="dict")
    yield
    if settings.database_url:
        from app.db.session import close_db
        await close_db()


app = FastAPI(
    title="Saksanalyse",
    description="AI-drevet analyse av norske stortingssaker",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
