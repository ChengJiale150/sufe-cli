import typer
import requests
from ..config import load_cookies

app = typer.Typer(help="SUFE IC空间管理系统 相关命令")

@app.command()
def check():
    """测试是否能成功访问 IC空间管理系统（携带 Cookie）"""
    cookies = load_cookies()
    if not cookies:
        typer.secho("未找到 Cookie 文件或文件损坏，请先运行 `sufe auth`", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
        
    req_cookies = {
        "ASP.NET_SessionId": cookies.asp_net_session_id,
        "SF_cookie_154": cookies.sf_cookie_154
    }
    
    url = "https://lclibrary.sufe.edu.cn/ClientWeb/xcus/ic2/Default.aspx"
    try:
        response = requests.get(url, cookies=req_cookies, allow_redirects=True, timeout=10)
        
        # 判断过期逻辑：如果是重定向到了登录页，或者状态码异常
        if "login.sufe.edu.cn" in response.url or response.status_code not in (200, 302, 304):
            typer.secho("Cookie 可能已过期，请求被重定向至登录页或访问失败，请重新运行 `sufe auth`", fg=typer.colors.YELLOW)
            raise typer.Exit(1)
        
        typer.secho("Cookie 有效！成功访问 IC空间管理系统。", fg=typer.colors.GREEN)
    except requests.RequestException as e:
        typer.secho(f"请求失败：{e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
