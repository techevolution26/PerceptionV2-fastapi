# app/core/config.py
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized, env-driven configuration (12-factor style). Every value here
    has a sane local-dev default so `docker compose up` works out of the box,
    but every value is expected to be overridden in production via env vars —
    see .env.example.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App ---
    APP_NAME: str = "Perception API"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = True
    API_PREFIX: str = "/api"

    # --- Security / auth ---
    SECRET_KEY: str = Field(default="change-me-in-prod-please-please-please")
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "perception-api"
    JWT_AUDIENCE: str = "perception-client"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 14
    ADMIN_SESSION_EXPIRE_MINUTES: int = 15
    GOOGLE_CLIENT_IDS: str = Field(
        default="",
        description="Comma-separated Android/iOS Google OAuth client IDs",
    )
    LOGIN_RATE_LIMIT_PER_MINUTE: int = 8
    ADMIN_SESSION_RATE_LIMIT_PER_MINUTE: int = 5
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    PASSWORD_RESET_RATE_LIMIT_PER_MINUTE: int = 5
    PASSWORD_RESET_URL: str = "http://localhost:3000/reset-password"
    MAIL_FROM: str = "no-reply@perception.local"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    RATE_LIMIT_FAIL_OPEN: bool = False

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                raise ValueError("DEBUG must be false in production")
            if (
                len(self.SECRET_KEY) < 32
                or self.SECRET_KEY == "change-me-in-prod-please-please-please"
            ):
                raise ValueError("A strong SECRET_KEY is required in production")
            if self.RATE_LIMIT_FAIL_OPEN:
                raise ValueError("RATE_LIMIT_FAIL_OPEN must be false in production")
            if not self.cors_origins_list:
                raise ValueError(
                    "CORS_ORIGINS must contain at least one origin in production"
                )
            if not self.SMTP_HOST or not self.MAIL_FROM:
                raise ValueError(
                    "SMTP_HOST and MAIL_FROM are required in production for account recovery"
                )
            if not self.PASSWORD_RESET_URL.startswith(("https://", "perception://")):
                raise ValueError(
                    "PASSWORD_RESET_URL must use https:// or perception:// in production"
                )
            if self.COMMENT_INTELLIGENCE_ENABLED and not self.OPENAI_API_KEY:
                raise ValueError(
                    "OPENAI_API_KEY is required when comment intelligence is enabled in production"
                )
        return self

    # --- Database ---
    DATABASE_URL: str = (
        "postgresql+asyncpg://perception:perception@postgres:5432/perception"
    )

    # --- Billing / Stripe ---
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_SUCCESS_URL: str = "http://localhost:3000/billing/success"
    STRIPE_CANCEL_URL: str = "http://localhost:3000/billing/cancel"
    STRIPE_PAST_DUE_GRACE_DAYS: int = 0
    STRIPE_PRICE_PROFESSIONAL: str = ""
    STRIPE_PRICE_RESEARCH: str = ""
    STRIPE_PRICE_BUSINESS: str = ""

    # --- Redis ---
    REDIS_URL: str = "redis://redis:6379/0"

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:3000"

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _split_origins(cls, v: str) -> str:
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # --- File storage ---
    STORAGE_ROOT: str = "/app/storage"
    STORAGE_URL_PREFIX: str = "/storage"
    PUBLIC_APP_URL: str = "http://localhost:8000"
    MAX_UPLOAD_MB: int = 10

    # --- Real-time (Pusher-protocol; soketi in docker-compose) ---
    PUSHER_APP_ID: str = "100001"
    PUSHER_APP_KEY: str = "perception-key"
    PUSHER_APP_SECRET: str = "perception-secret"
    PUSHER_HOST: str = "soketi"
    PUSHER_PORT: int = 6001
    PUSHER_SCHEME: str = "http"
    PUSHER_CLUSTER: str = "eu"  # kept for client compatibility; soketi ignores it

    # --- Networking tuning (East-Africa-aware, carried over from the Laravel config) ---
    UPSTREAM_TIMEOUT_SECONDS: float = 15.0

    # --- Comment intelligence provider ---
    COMMENT_INTELLIGENCE_ENABLED: bool = False
    COMMENT_INTELLIGENCE_MODEL: str = "gpt-5.6-luna"
    COMMENT_INTELLIGENCE_BATCH_SIZE: int = 10
    COMMENT_INTELLIGENCE_INTERVAL_SECONDS: int = 60
    COMMENT_INTELLIGENCE_COOLDOWN_MAX_SECONDS: int = 86400
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
