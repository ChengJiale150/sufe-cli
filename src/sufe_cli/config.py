import json
from pathlib import Path
from pydantic import BaseModel, Field

COOKIE_FILE_PATH = Path.home() / ".sufe-cli" / "cookie.json"

class LclibraryCookies(BaseModel):
    asp_net_session_id: str = Field(..., alias="ASP.NET_SessionId")
    sf_cookie_154: str = Field(..., alias="SF_cookie_154")

class SufeCookies(BaseModel):
    lclibrary: LclibraryCookies

def get_cookie_path() -> Path:
    return COOKIE_FILE_PATH

def save_cookies(cookies: SufeCookies) -> None:
    path = get_cookie_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(cookies.model_dump_json(by_alias=True, indent=2))

def load_cookies() -> SufeCookies | None:
    path = get_cookie_path()
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return SufeCookies(**data)
    except Exception:
        return None
