import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from sufe_cli.config import STATE_FILE_PATH

PORTAL_ORIGIN = "https://portal.sufe.edu.cn"


def load_storage_state(path: Path | None = None) -> dict[str, Any] | None:
    actual_path = STATE_FILE_PATH if path is None else path
    if not actual_path.exists():
        return None
    try:
        data = json.loads(actual_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def load_portal_token(path: Path | None = None) -> str | None:
    state = load_storage_state(path)
    if state is None:
        return None

    for origin_entry in state.get("origins", []):
        if not isinstance(origin_entry, dict) or origin_entry.get("origin") != PORTAL_ORIGIN:
            continue
        for item in origin_entry.get("localStorage", []):
            if not isinstance(item, dict) or item.get("name") != "vuex":
                continue
            try:
                vuex_data = json.loads(str(item.get("value", "{}")))
            except json.JSONDecodeError:
                return None
            token = vuex_data.get("user", {}).get("token")
            return token if isinstance(token, str) and token else None
    return None


def extract_cookies_for_domain(
    domain: str,
    names: Iterable[str],
    path: Path | None = None,
) -> dict[str, str]:
    state = load_storage_state(path)
    if state is None:
        return {}

    wanted = set(names)
    result: dict[str, str] = {}
    for cookie in state.get("cookies", []):
        if not isinstance(cookie, dict):
            continue
        name = cookie.get("name")
        value = cookie.get("value")
        cookie_domain = cookie.get("domain")
        if not isinstance(name, str) or not isinstance(value, str) or not isinstance(cookie_domain, str):
            continue
        if name in wanted and _domain_matches(domain, cookie_domain):
            result[name] = value
    return result


def _domain_matches(host: str, cookie_domain: str) -> bool:
    normalized = cookie_domain.lstrip(".")
    return host == normalized or host.endswith(f".{normalized}")
