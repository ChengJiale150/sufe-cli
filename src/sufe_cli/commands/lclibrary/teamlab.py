import typer
import json
from sufe_cli.utils.network import sufe_get
from .utils import parse_data, validate_reservation, get_today_str

app = typer.Typer(help="SUFE 小组研习室 相关命令")

@app.command(name="list")
def list_teamlab(date: str = typer.Argument(default_factory=get_today_str, help="查询日期, 例如20260501, 默认为今天")):
    """列出指定日期的小组研习室状态"""
    url = f"https://lclibrary.sufe.edu.cn/ClientWeb/pro/ajax/device.aspx?kind_id=100811029&date={date}&act=get_rsv_sta"
    
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
def reserve_teamlab(
    id: str = typer.Argument(..., help="预约的研讨室 ID"),
    name: str = typer.Argument(..., help="预约名称"),
    members: str = typer.Argument(..., help="预约的成员学号列表, 逗号分隔 (如: 2023110603,2023110604)"),
    start: str = typer.Argument(..., help="起始时间, 格式为 2026-05-01 10:40"),
    end: str = typer.Argument(..., help="结束时间, 格式为 2026-05-01 13:10")
):
    """预约小组研习室"""
    # 1. 本地规则校验
    try:
        start_dt, end_dt, member_list = validate_reservation(start=start, end=end, members=members)
    except ValueError as e:
        typer.secho(f"校验失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
        
    # 2. 准备请求参数
    params = {
        "dev_id": id,
        "lab_id": "100811022",
        "kind_id": "100811029",
        "type": "dev",
        "term": "",
        "test_name": name,
        "min_user": "3",
        "max_user": "10",
        "mb_list": ",".join(member_list),
        "start": start_dt.strftime("%Y-%m-%d %H:%M"),
        "end": end_dt.strftime("%Y-%m-%d %H:%M"),
        "act": "set_resv"
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
