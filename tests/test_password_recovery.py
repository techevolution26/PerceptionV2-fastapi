from app.schemas.user import ChangePasswordRequest, RegisterRequest, ResetPasswordRequest


def test_password_policy_is_shared_by_registration_and_reset():
    strong = "Secure123!"
    assert RegisterRequest(name="Demo", email="demo@example.com", password=strong, password_confirmation=strong).password == strong
    assert ResetPasswordRequest(token="x" * 32, password=strong, password_confirmation=strong).password == strong
    assert ChangePasswordRequest(current_password="old", password=strong, password_confirmation=strong).password == strong


def test_weak_password_is_rejected():
    try:
        RegisterRequest(name="Demo", email="demo@example.com", password="password", password_confirmation="password")
    except Exception as exc:
        assert "uppercase" in str(exc).lower()
    else:
        raise AssertionError("Weak password should be rejected")
