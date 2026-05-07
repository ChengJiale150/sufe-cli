import json

import pytest

from sufe_cli.config import (
    AuthConfig,
    AuthMode,
    auth_config_exists,
    load_auth_config,
    require_auto_credentials,
    save_auth_config,
)
from sufe_cli.errors import AuthConfigMissingError


def test_missing_auth_config_defaults_to_manual(tmp_path) -> None:
    assert load_auth_config(tmp_path / "missing.json").mode == AuthMode.MANUAL


def test_auth_config_exists(tmp_path) -> None:
    missing_path = tmp_path / "missing.json"
    assert auth_config_exists(missing_path) is False

    existing_path = tmp_path / "auth.json"
    save_auth_config(AuthConfig(mode=AuthMode.MANUAL), existing_path)
    assert auth_config_exists(existing_path) is True


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
    with pytest.raises(AuthConfigMissingError, match="自动登录配置缺少"):
        require_auto_credentials(AuthConfig(mode=AuthMode.AUTO, username="20230001"))
