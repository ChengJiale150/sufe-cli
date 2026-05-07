import json
from typing import Annotated

import typer

from sufe_cli.cli_helpers import cli_error_boundary
from sufe_cli.errors import InvalidResponseError

from .client import LCLIBRARY_BASE, sufe_get
from .multimedia import app as multimedia_app
from .silentcabin import app as silentcabin_app
from .teamlab import app as teamlab_app

app = typer.Typer(help="SUFE Lclibrary 相关命令")

app.add_typer(teamlab_app, name="teamlab")
app.add_typer(silentcabin_app, name="silentcabin")
app.add_typer(multimedia_app, name="multimedia")

SearchQueryArgument = Annotated[str, typer.Argument(help="搜索的姓名关键字，支持部分名称")]


@app.command(name="search")
@cli_error_boundary
def search_account(query: SearchQueryArgument):
    """根据姓名模糊搜索学号"""
    url = f"{LCLIBRARY_BASE}/ClientWeb/pro/ajax/data/searchAccount.aspx"
    params = {"term": query}

    response = sufe_get(url, params=params)

    try:
        data = response.json()
    except (json.JSONDecodeError, TypeError) as e:
        raise InvalidResponseError(f"解析 JSON 失败: {e}") from e

    if not isinstance(data, list):
        raise InvalidResponseError("API 返回的数据格式异常，不是预期的列表格式。")

    labels = [item.get("label") for item in data if item.get("label")]

    if not labels:
        typer.secho(f"未找到与 '{query}' 匹配的账号信息。", fg=typer.colors.YELLOW)
    else:
        typer.echo(json.dumps(labels, ensure_ascii=False, indent=2))
