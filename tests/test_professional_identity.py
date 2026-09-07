from app.services.professional_taxonomy import INDUSTRIES, ROLES, ROLE_MAP, validate_identity_selection


def test_professional_taxonomy_is_broad_and_complete():
    assert len(INDUSTRIES) >= 30
    assert len(ROLES) >= 180
    industry_codes = {item["code"] for item in INDUSTRIES}
    assert all(role["industry_code"] in industry_codes for role in ROLES)
    assert len(ROLE_MAP) == len(ROLES)


def test_primary_role_must_be_selected():
    validate_identity_selection(["technology"], ["software_engineer"], "software_engineer")

    try:
        validate_identity_selection(["technology"], ["software_engineer"], "physicist")
    except ValueError as exc:
        assert "Primary professional role" in str(exc)
    else:
        raise AssertionError("Expected primary-role validation to fail")
