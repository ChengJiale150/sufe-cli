import json

import pytest

from sufe_cli.client.auth_config import (
    AuthConfig,
    AuthMode,
    load_auth_config,
    require_auto_credentials,
    save_auth_config,
)


def test_missing_auth_config_defaults_to_manual(tmp_path) -> None:
    assert load_auth_config(tmp_path / "missing.json").mode == AuthMode.MANUAL


def test_save_and_load_auto_config_plaintext(tmp_path) -> None:
    path = tmp_path / "auth.json"
    save_auth_config(AuthConfig(mode=AuthMode.AUTO, username="20230001", password="plain-password"), path)

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw == {"mode": "auto", "username": "20230001", "password": "plain-password"}

    loaded = load_auth_config(path)
    assert loaded.mode == AuthMode.AUTO
    assert loaded.username == "20230001"
    assert loaded.password == "plain-password"


def test_require_auto_credentials_rejects_incomplete_auto_config() -> None:
    with pytest.raises(ValueError, match="自动登录配置缺少"):
        require_auto_credentials(AuthConfig(mode=AuthMode.AUTO, username="20230001"))
