import json

from sufe_cli.client.state import extract_cookies_for_domain, load_portal_token


def test_load_portal_token_from_playwright_state(tmp_path) -> None:
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            {
                "cookies": [],
                "origins": [
                    {
                        "origin": "https://portal.sufe.edu.cn",
                        "localStorage": [{"name": "vuex", "value": json.dumps({"user": {"token": "portal-token"}})}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert load_portal_token(path) == "portal-token"


def test_extract_cookies_for_domain_matches_exact_and_parent_domains(tmp_path) -> None:
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            {
                "cookies": [
                    {"name": "ASP.NET_SessionId", "value": "session", "domain": "lclibrary.sufe.edu.cn"},
                    {"name": "SF_cookie_154", "value": "sf", "domain": ".sufe.edu.cn"},
                    {"name": "other", "value": "ignored", "domain": "lclibrary.sufe.edu.cn"},
                    {"name": "ASP.NET_SessionId", "value": "wrong", "domain": "example.com"},
                ],
                "origins": [],
            }
        ),
        encoding="utf-8",
    )

    cookies = extract_cookies_for_domain(
        "lclibrary.sufe.edu.cn",
        ["ASP.NET_SessionId", "SF_cookie_154"],
        path,
    )

    assert cookies == {"ASP.NET_SessionId": "session", "SF_cookie_154": "sf"}
