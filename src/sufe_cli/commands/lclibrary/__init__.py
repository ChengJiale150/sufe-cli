import typer
import requests
import json
from sufe_cli.config import load_cookies
from sufe_cli.utils.network import get_default_headers
from .teamlab import app as teamlab_app
from .silentcabin import app as silentcabin_app
from .multimedia import app as multimedia_app

app = typer.Typer(help="SUFE Lclibrary 相关命令")

app.add_typer(teamlab_app, name="teamlab")
app.add_typer(silentcabin_app, name="silentcabin")
app.add_typer(multimedia_app, name="multimedia")

@app.command()
def check():
    """测试是否能成功访问 IC空间管理系统（携带 Cookie）"""
    cookies = load_cookies()
    if not cookies:
        typer.secho("未找到 Cookie 文件或文件损坏，请先运行 `sufe auth`", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
        
    req_cookies = {
        "ASP.NET_SessionId": cookies.lclibrary.asp_net_session_id,
        "SF_cookie_154": cookies.lclibrary.sf_cookie_154
    }
    
    url = "https://lclibrary.sufe.edu.cn/ClientWeb/xcus/ic2/Default.aspx"
    try:
        response = requests.get(url, cookies=req_cookies, headers=get_default_headers(), allow_redirects=True, timeout=10)
        
        # 判断过期逻辑：如果是重定向到了登录页，或者状态码异常
        if "login.sufe.edu.cn" in response.url or response.status_code not in (200, 302, 304):
            typer.secho("Cookie 可能已过期，请求被重定向至登录页或访问失败，请重新运行 `sufe auth`", fg=typer.colors.YELLOW)
            raise typer.Exit(1)
        
        typer.secho("Cookie 有效！成功访问 IC空间管理系统。", fg=typer.colors.GREEN)
    except requests.RequestException as e:
        typer.secho(f"请求失败：{e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

@app.command(name="search")
def search_account(query: str = typer.Argument(..., help="搜索的姓名关键字，支持部分名称")):
    """根据姓名模糊搜索学号"""
    cookies = load_cookies()
    if not cookies:
        typer.secho("未找到 Cookie 文件或文件损坏，请先运行 `sufe auth`", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
        
    req_cookies = {
        "ASP.NET_SessionId": cookies.lclibrary.asp_net_session_id,
        "SF_cookie_154": cookies.lclibrary.sf_cookie_154
    }
    
    url = "https://lclibrary.sufe.edu.cn/ClientWeb/pro/ajax/data/searchAccount.aspx"
    params = {"term": query}
    
    try:
        response = requests.get(
            url, 
            params=params,
            cookies=req_cookies, 
            headers=get_default_headers(), 
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        typer.secho(f"网络请求或解析失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
        
    if not isinstance(data, list):
        typer.secho("API 返回的数据格式异常，不是预期的列表格式。", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
        
    labels = [item.get("label") for item in data if item.get("label")]
    
    if not labels:
        typer.secho(f"未找到与 '{query}' 匹配的账号信息。", fg=typer.colors.YELLOW)
    else:
        typer.echo(json.dumps(labels, ensure_ascii=False, indent=2))
