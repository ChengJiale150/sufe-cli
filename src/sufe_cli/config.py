import json
from pathlib import Path
from pydantic import BaseModel, Field

COOKIE_FILE_PATH = Path.home() / ".sufe-cli" / "cookie.json"
STATE_FILE_PATH = Path.home() / ".sufe-cli" / "state.json"
USER_FILE_PATH = Path.home() / ".sufe-cli" / "user.json"


class LclibraryCookies(BaseModel):
    asp_net_session_id: str = Field(..., alias="ASP.NET_SessionId")
    sf_cookie_154: str = Field(..., alias="SF_cookie_154")


class SufeCookies(BaseModel):
    lclibrary: LclibraryCookies


class UserProfile(BaseModel):
    user_id: str
    user_name: str
    organization_name: str


def save_cookies(cookies: SufeCookies) -> None:
    COOKIE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(COOKIE_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(cookies.model_dump_json(by_alias=True, indent=2))


def load_cookies() -> SufeCookies | None:
    if not COOKIE_FILE_PATH.exists():
        return None
    try:
        with open(COOKIE_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return SufeCookies(**data)
    except Exception:
        return None


def save_user_profile(profile: UserProfile) -> None:
    USER_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(USER_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(profile.model_dump_json(indent=2))


def load_user_profile() -> UserProfile | None:
    if not USER_FILE_PATH.exists():
        return None
    try:
        with open(USER_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return UserProfile(**data)
    except Exception:
        return None
