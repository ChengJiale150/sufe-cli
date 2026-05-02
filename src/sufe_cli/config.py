import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict

APP_DIR = Path.home() / ".sufe-cli"
STATE_FILE_PATH = APP_DIR / "state.json"
AUTH_FILE_PATH = APP_DIR / "auth.json"


class AuthMode(str, Enum):
    MANUAL = "manual"
    AUTO = "auto"


class AuthConfig(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    mode: AuthMode = AuthMode.MANUAL
    username: str | None = None
    password: str | None = None


def load_auth_config(path: Path | None = None) -> AuthConfig:
    actual_path = AUTH_FILE_PATH if path is None else path
    if not actual_path.exists():
        return AuthConfig()

    try:
        data = json.loads(actual_path.read_text(encoding="utf-8"))
        return AuthConfig.model_validate(data)
    except Exception:
        return AuthConfig()


def save_auth_config(config: AuthConfig, path: Path | None = None) -> None:
    actual_path = AUTH_FILE_PATH if path is None else path
    actual_path.parent.mkdir(parents=True, exist_ok=True)
    actual_path.write_text(config.model_dump_json(exclude_none=True, indent=2), encoding="utf-8")


def require_auto_credentials(config: AuthConfig) -> tuple[str, str]:
    if config.mode != AuthMode.AUTO or not config.username or not config.password:
        msg = "自动登录配置缺少学号或密码，请运行 `sufe config set --mode auto --username <username> --password <password>`"
        raise ValueError(msg)
    return config.username, config.password
