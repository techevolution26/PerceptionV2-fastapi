# app/main.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    auth,
    analytics,
    subscriptions,
    verification,
    broadcasting,
    comments,
    conversations,
    health,
    likes,
    notifications,
    perceptions,
    search,
    topics,
    users,
)
from app.core.config import get_settings
from app.services.scheduler import start_scheduler, stop_scheduler

settings = get_settings()

logging.basicConfig(level=logging.INFO if not settings.DEBUG else logging.DEBUG)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    scheduler = start_scheduler()
    yield
    stop_scheduler(scheduler)


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serves uploaded avatars/media at /storage/... — matches Laravel's public
# disk convention, which the frontend's next.config.js already rewrites
# `/storage/:path*` requests to hit.
app.mount(settings.STORAGE_URL_PREFIX, StaticFiles(directory=settings.STORAGE_ROOT), name="storage")

for router in (
    health,
    auth,
    analytics,
    subscriptions,
    verification,
    users,
    topics,
    perceptions,
    likes,
    comments,
    conversations,
    notifications,
    search,
    broadcasting,
):
    app.include_router(router.router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    return {"service": settings.APP_NAME, "docs": "/docs"}
