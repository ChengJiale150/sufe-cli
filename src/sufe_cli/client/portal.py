from pydantic import BaseModel
import requests

from .state import load_portal_token

USER_PROFILE_URL = "https://authx-service.sufe.edu.cn/personal/api/v1/personal/me/user"


class UserProfile(BaseModel):
    user_id: str
    user_name: str
    organization_name: str


def get_portal_headers(token: str) -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "x-id-token": token,
    }


def fetch_user_profile(timeout: int = 30) -> UserProfile | None:
    token = load_portal_token()
    if token is None:
        return None

    response = requests.get(USER_PROFILE_URL, headers=get_portal_headers(token), timeout=timeout)
    if response.status_code != 200:
        return None

    payload = response.json()
    data = payload.get("data", {})
    attrs = data.get("attributes", {})
    return UserProfile(
        user_id=attrs.get("userUid", ""),
        user_name=attrs.get("userName", ""),
        organization_name=attrs.get("organizationName", ""),
    )
