import typer
import requests
import json
from sufe_cli.config import load_cookies
from sufe_cli.utils import get_default_headers
from .utils import parse_data, validate_reservation

app = typer.Typer(help="SUFE 多媒体制作室 相关命令")

@app.command(name="list")
def list_multimedia(date: str = typer.Argument(..., help="查询日期, 例如20260502")):
    """列出指定日期的多媒体制作室状态"""
    cookies = load_cookies()
    if not cookies:
        typer.secho("未找到 Cookie 文件或文件损坏，请先运行 `sufe auth`", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
        
    req_cookies = {
        "ASP.NET_SessionId": cookies.lclibrary.asp_net_session_id,
        "SF_cookie_154": cookies.lclibrary.sf_cookie_154
    }
    
    url = f"https://lclibrary.sufe.edu.cn/ClientWeb/pro/ajax/device.aspx?kind_id=100811035&date={date}&act=get_rsv_sta"
    
    try:
        response = requests.get(url, cookies=req_cookies, headers=get_default_headers(), timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        typer.secho(f"请求失败或解析 JSON 失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
        
    if data.get("ret") != 1:
        typer.secho(f"服务器返回错误: {data.get('msg')}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
        
    try:
        result = parse_data(data, date)
    except Exception as e:
        typer.secho(f"处理数据时出错: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
        
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))

@app.command(name="reserve")
def reserve_multimedia(
    id: str = typer.Argument(..., help="预约的多媒体制作室 ID"),
    start: str = typer.Argument(..., help="起始时间, 格式为 2026-05-01 13:40"),
    end: str = typer.Argument(..., help="结束时间, 格式为 2026-05-01 16:00")
):
    """预约多媒体制作室"""
    # 1. 本地规则校验 (无需传递 members 参数, 最大时长3小时, 最小时长10分钟)
    try:
        start_dt, end_dt, _ = validate_reservation(start=start, end=end, min_hours=10/60, max_hours=3)
    except ValueError as e:
        typer.secho(f"校验失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
        
    # 2. 读取 Cookie
    cookies = load_cookies()
    if not cookies:
        typer.secho("未找到 Cookie 文件或文件损坏，请先运行 `sufe auth`", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
        
    req_cookies = {
        "ASP.NET_SessionId": cookies.lclibrary.asp_net_session_id,
        "SF_cookie_154": cookies.lclibrary.sf_cookie_154
    }
    
    # 3. 准备请求参数
    params = {
        "dev_id": id,
        "lab_id": "115187637",
        "kind_id": "100811035",
        "act": "set_resv",
        "start": start_dt.strftime("%Y-%m-%d %H:%M"),
        "end": end_dt.strftime("%Y-%m-%d %H:%M")
    }
    
    url = "https://lclibrary.sufe.edu.cn/ClientWeb/pro/ajax/reserve.aspx"
    
    # 4. 发起预约请求
    try:
        response = requests.get(
            url, 
            params=params,
            cookies=req_cookies, 
            headers=get_default_headers(), 
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        typer.secho(f"网络请求或解析失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
        
    # 5. 分析返回结果
    if data.get("ret") == 1:
        typer.secho("✅ 预约成功！", fg=typer.colors.GREEN)
        if data.get("msg") and data.get("msg").lower() != "ok":
            typer.secho(f"服务器返回消息: {data.get('msg')}", fg=typer.colors.YELLOW)
    else:
        err_msg = data.get("msg", "未知错误")
        typer.secho(f"❌ 预约失败: {err_msg}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
