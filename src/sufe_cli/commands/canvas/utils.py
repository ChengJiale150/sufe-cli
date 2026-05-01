import typer

from sufe_cli.client.http import sufe_get_canvas


def has_next_page(response) -> bool:
    """检查 Canvas Link header 中是否有 rel=next 的分页链接"""
    link_header = response.headers.get("Link", "")
    for part in link_header.split(","):
        if 'rel="next"' in part:
            return True
    return False


def fetch_all_pages(url: str, params: dict | None = None) -> list:
    """获取 Canvas API 所有分页数据"""
    all_data: list = []
    page = 1
    current_params = dict(params) if params else {}

    while True:
        current_params["page"] = page
        response = sufe_get_canvas(url, params=current_params)

        try:
            data = response.json()
        except Exception as e:
            typer.secho(f"解析 JSON 失败: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

        if not isinstance(data, list):
            typer.secho("API 返回的数据格式异常，不是预期的列表格式。", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

        all_data.extend(data)

        if not data or not has_next_page(response):
            break

        page += 1

    return all_data
