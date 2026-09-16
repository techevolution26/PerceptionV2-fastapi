from __future__ import annotations

from pathlib import Path

from app.services.privacy_contract_guard import (
    creator_discoverability_allowed,
    intelligence_participation_allowed,
)


def test_conversation_quality_gate_document_exists():
    assert Path("docs/DISCOVERY_25_CONVERSATION_QUALITY_GATE.md").is_file()


def test_privacy_controls_default_to_allowed_for_existing_accounts():
    class ExistingUser:
        privacy_preferences = None

    user = ExistingUser()
    assert intelligence_participation_allowed(user) is True
    assert creator_discoverability_allowed(user) is True


def test_privacy_controls_can_disable_derived_surfaces():
    class RestrictedUser:
        privacy_preferences = {
            "intelligence_participation": False,
            "creator_discoverability": False,
        }

    user = RestrictedUser()
    assert intelligence_participation_allowed(user) is False
    assert creator_discoverability_allowed(user) is False


def test_perception_intelligence_experience_document_exists():
    assert Path("docs/DISCOVERY_26_PERCEPTION_INTELLIGENCE_EXPERIENCE.md").is_file()
