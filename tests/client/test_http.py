from sufe_cli.client.network import DEFAULT_USER_AGENT, get_default_headers


def test_default_headers_include_optional_browser_request_fields() -> None:
    headers = get_default_headers(referer="https://example.test/", requested_with="XMLHttpRequest")

    assert headers == {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://example.test/",
        "X-Requested-With": "XMLHttpRequest",
    }
