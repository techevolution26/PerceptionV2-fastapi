# app/main.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    auth,
    analytics,
    admin,
    subscriptions,
    verification,
    broadcasting,
    comments,
    conversations,
    health,
    likes,
    notifications,
    investigation_threads,
    perceptions,
    reports,
    perception_moderation,
    recommendations,
    search,
    saved_perceptions,
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


docs_enabled = settings.ENVIRONMENT != "production"

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_url="/openapi.json" if docs_enabled else None,
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


app.add_middleware(SecurityHeadersMiddleware)

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
app.mount(
    settings.STORAGE_URL_PREFIX,
    StaticFiles(directory=settings.STORAGE_ROOT),
    name="storage",
)

for router in (
    health,
    auth,
    analytics,
    admin,
    subscriptions,
    verification,
    users,
    topics,
    perceptions,
    investigation_threads,
    reports,
    perception_moderation,
    recommendations,
    saved_perceptions,
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
