import typer
import json
from sufe_cli.client.http import sufe_get
from .teamlab import app as teamlab_app
from .silentcabin import app as silentcabin_app
from .multimedia import app as multimedia_app

app = typer.Typer(help="SUFE Lclibrary 相关命令")

app.add_typer(teamlab_app, name="teamlab")
app.add_typer(silentcabin_app, name="silentcabin")
app.add_typer(multimedia_app, name="multimedia")


@app.command(name="search")
def search_account(query: str = typer.Argument(..., help="搜索的姓名关键字，支持部分名称")):
    """根据姓名模糊搜索学号"""
    url = "https://lclibrary.sufe.edu.cn/ClientWeb/pro/ajax/data/searchAccount.aspx"
    params = {"term": query}

    response = sufe_get(url, params=params)

    try:
        data = response.json()
    except Exception as e:
        typer.secho(f"解析 JSON 失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    if not isinstance(data, list):
        typer.secho("API 返回的数据格式异常，不是预期的列表格式。", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    labels = [item.get("label") for item in data if item.get("label")]

    if not labels:
        typer.secho(f"未找到与 '{query}' 匹配的账号信息。", fg=typer.colors.YELLOW)
    else:
        typer.echo(json.dumps(labels, ensure_ascii=False, indent=2))
