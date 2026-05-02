import pytest

from sufe_cli.client import portal
from sufe_cli.errors import AuthExpiredError


def test_ensure_user_profile_refreshes_portal_state_before_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    profiles = [
        None,
        portal.UserProfile(user_id="20230001", user_name="Student", organization_name="School"),
    ]
    refreshed = False

    def fake_ensure_portal_state() -> bool:
        nonlocal refreshed
        refreshed = True
        return True

    monkeypatch.setattr(portal, "fetch_user_profile", lambda timeout=30: profiles.pop(0))
    monkeypatch.setattr(portal, "ensure_portal_state", fake_ensure_portal_state)

    profile = portal.ensure_user_profile()

    assert profile.user_id == "20230001"
    assert refreshed is True


def test_ensure_user_profile_raises_when_refresh_cannot_restore_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(portal, "fetch_user_profile", lambda timeout=30: None)
    monkeypatch.setattr(portal, "ensure_portal_state", lambda: False)

    with pytest.raises(AuthExpiredError):
        portal.ensure_user_profile()
