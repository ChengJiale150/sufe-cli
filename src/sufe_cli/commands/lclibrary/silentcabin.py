import typer
import json
from sufe_cli.client.http import sufe_get
from .utils import parse_data, validate_reservation, get_today_str

app = typer.Typer(help="SUFE 静音舱 相关命令")


@app.command(name="list")
def list_silentcabin(
    date: str = typer.Argument(default_factory=get_today_str, help="查询日期, 例如20260430, 默认为今天"),
):
    """列出指定日期的静音舱状态"""
    url = f"https://lclibrary.sufe.edu.cn/ClientWeb/pro/ajax/device.aspx?kind_id=126386594&date={date}&act=get_rsv_sta"

    response = sufe_get(url)
    try:
        data = response.json()
    except Exception as e:
        typer.secho(f"解析 JSON 失败: {e}", fg=typer.colors.RED, err=True)
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
def reserve_silentcabin(
    id: str = typer.Argument(..., help="预约的静音舱 ID"),
    start: str = typer.Argument(..., help="起始时间, 格式为 2026-05-01 13:40"),
    end: str = typer.Argument(..., help="结束时间, 格式为 2026-05-01 17:40"),
):
    """预约静音舱"""
    # 1. 本地规则校验 (无需传递 members 参数)
    try:
        start_dt, end_dt, _ = validate_reservation(start=start, end=end)
    except ValueError as e:
        typer.secho(f"校验失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    # 2. 准备请求参数
    params = {
        "dev_id": id,
        "lab_id": "126386596",
        "kind_id": "126386594",
        "act": "set_resv",
        "start": start_dt.strftime("%Y-%m-%d %H:%M"),
        "end": end_dt.strftime("%Y-%m-%d %H:%M"),
    }

    url = "https://lclibrary.sufe.edu.cn/ClientWeb/pro/ajax/reserve.aspx"

    # 3. 发起预约请求
    response = sufe_get(url, params=params)
    try:
        data = response.json()
    except Exception as e:
        typer.secho(f"解析失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    # 4. 分析返回结果
    if data.get("ret") == 1:
        typer.secho("✅ 预约成功！", fg=typer.colors.GREEN)
        if data.get("msg") and data.get("msg").lower() != "ok":
            typer.secho(f"服务器返回消息: {data.get('msg')}", fg=typer.colors.YELLOW)
    else:
        err_msg = data.get("msg", "未知错误")
        typer.secho(f"❌ 预约失败: {err_msg}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
