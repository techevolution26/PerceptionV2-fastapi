from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_demo_verified_users_use_canonical_verified_status():
    source = (ROOT / "app" / "seed_demo.py").read_text(encoding="utf-8")
    assert '"VERIFIED" if verified_demo_user else "NOT_APPLIED"' in source
    assert '"APPROVED" if verified_demo_user else "NOT_APPLIED"' not in source


def test_verification_application_approval_is_distinct_from_user_status():
    source = (ROOT / "app" / "api" / "routes" / "verification.py").read_text(
        encoding="utf-8"
    )
    assert 'application.status = "APPROVED" if approved else "REJECTED"' in source
    assert 'user.verification_status = "VERIFIED" if approved else "REJECTED"' in source
