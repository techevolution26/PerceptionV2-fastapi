import os
from dataclasses import dataclass
from typing import AsyncIterator, Iterator

import httpx
import pytest


BASE_URL = os.getenv("ACCEPTANCE_BASE_URL", "http://localhost:8000").rstrip("/")
ADMIN_EMAIL = os.getenv("ACCEPTANCE_ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.getenv("ACCEPTANCE_ADMIN_PASSWORD", "")
PLATFORM_ADMIN_EMAIL = os.getenv("ACCEPTANCE_PLATFORM_ADMIN_EMAIL", "").strip().lower()
PLATFORM_ADMIN_PASSWORD = os.getenv("ACCEPTANCE_PLATFORM_ADMIN_PASSWORD", "")
GOOGLE_EXISTING_ID_TOKEN = os.getenv("ACCEPTANCE_GOOGLE_EXISTING_ID_TOKEN", "")
GOOGLE_NEW_ID_TOKEN = os.getenv("ACCEPTANCE_GOOGLE_NEW_ID_TOKEN", "")
ANALYTICS_EMAIL = os.getenv("ACCEPTANCE_ANALYTICS_EMAIL", "").strip().lower()
ANALYTICS_PASSWORD = os.getenv("ACCEPTANCE_ANALYTICS_PASSWORD", "")

pytestmark = pytest.mark.acceptance


@dataclass(frozen=True)
class Actor:
    name: str
    email: str
    password: str
    token: str
    user_id: int


@pytest.fixture
async def api() -> AsyncIterator[httpx.AsyncClient]:
    """Per-test async client; never shared across pytest event loops."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=20.0) as client:
        yield client


@pytest.fixture(scope="session")
def bootstrap_api() -> Iterator[httpx.Client]:
    """Session bootstrap client kept synchronous to avoid async loop ownership."""
    with httpx.Client(base_url=BASE_URL, timeout=20.0) as client:
        yield client


def _actor_from_response(name: str, email: str, response: httpx.Response) -> Actor:
    if not response.is_success:
        pytest.fail(
            f"Acceptance actor registration failed for {email}: "
            f"HTTP {response.status_code} {response.text[:1000]}"
        )
    body = response.json()
    return Actor(
        name=name,
        email=email,
        password="Acceptance9!Gate",
        token=body["token"],
        user_id=body["user"]["id"],
    )


async def register_actor(api: httpx.AsyncClient, *, name: str, email: str) -> Actor:
    password = "Acceptance9!Gate"
    response = await api.post(
        "/api/register",
        json={
            "name": name,
            "email": email,
            "password": password,
            "password_confirmation": password,
        },
    )
    return _actor_from_response(name, email, response)


def register_actor_sync(api: httpx.Client, *, name: str, email: str) -> Actor:
    password = "Acceptance9!Gate"
    response = api.post(
        "/api/register",
        json={
            "name": name,
            "email": email,
            "password": password,
            "password_confirmation": password,
        },
    )
    return _actor_from_response(name, email, response)


@pytest.fixture(scope="session")
def actors(bootstrap_api: httpx.Client) -> dict[str, Actor]:
    """Create acceptance actors once using the synchronous bootstrap client."""
    suffix = os.getenv("ACCEPTANCE_RUN_ID", "release-gate")
    return {
        "alice": register_actor_sync(bootstrap_api, name="Acceptance Alice", email=f"acceptance-alice+{suffix}@example.com"),
        "bob": register_actor_sync(bootstrap_api, name="Acceptance Bob", email=f"acceptance-bob+{suffix}@example.com"),
        "charlie": register_actor_sync(bootstrap_api, name="Acceptance Charlie", email=f"acceptance-charlie+{suffix}@example.com"),
    }


def auth(actor: Actor) -> dict[str, str]:
    return {"Authorization": f"Bearer {actor.token}"}


@pytest.fixture(scope="session")
def topic_id(bootstrap_api: httpx.Client) -> int:
    response = bootstrap_api.get("/api/topics")
    response.raise_for_status()
    body = response.json()
    topics = body.get("topics", body) if isinstance(body, dict) else body
    if not topics:
        pytest.fail("Acceptance environment has no seeded topics.")
    return int(topics[0]["id"])


@pytest.fixture(scope="session")
def admin_token(bootstrap_api: httpx.Client) -> str:
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        pytest.skip("Set ACCEPTANCE_ADMIN_EMAIL and ACCEPTANCE_ADMIN_PASSWORD for admin release-gate tests.")
    login = bootstrap_api.post("/api/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if not login.is_success:
        pytest.fail(
            f"SUPER_ADMIN acceptance login failed: HTTP {login.status_code} "
            f"{login.text[:1000]}"
        )
    login_body = login.json()
    user = login_body["user"]
    if user["role"] != "SUPER_ADMIN":
        pytest.fail("ACCEPTANCE_ADMIN_EMAIL is not a SUPER_ADMIN.")
    session = bootstrap_api.post(
        "/api/admin/session",
        headers={"Authorization": f"Bearer {login_body['token']}"},
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    if not session.is_success:
        pytest.fail(
            f"SUPER_ADMIN session reauthentication failed: HTTP {session.status_code} "
            f"{session.text[:1000]}"
        )
    return session.json()["token"]


@pytest.fixture(scope="session")
def platform_admin_token(bootstrap_api: httpx.Client) -> str:
    if not PLATFORM_ADMIN_EMAIL or not PLATFORM_ADMIN_PASSWORD:
        pytest.skip("Set ACCEPTANCE_PLATFORM_ADMIN_EMAIL and ACCEPTANCE_PLATFORM_ADMIN_PASSWORD for the ADMIN boundary test.")
    login = bootstrap_api.post("/api/login", json={"email": PLATFORM_ADMIN_EMAIL, "password": PLATFORM_ADMIN_PASSWORD})
    login.raise_for_status()
    login_body = login.json()
    user = login_body["user"]
    if user["role"] != "ADMIN":
        pytest.fail("ACCEPTANCE_PLATFORM_ADMIN_EMAIL is not an ADMIN account.")
    return login_body["token"]
