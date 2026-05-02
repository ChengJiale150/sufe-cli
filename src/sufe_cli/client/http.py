DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
)


def get_default_headers(
    *,
    accept: str = "application/json, text/javascript, */*; q=0.01",
    referer: str | None = None,
    requested_with: str | None = None,
) -> dict[str, str]:
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": accept,
    }
    if referer is not None:
        headers["Referer"] = referer
    if requested_with is not None:
        headers["X-Requested-With"] = requested_with
    return headers
