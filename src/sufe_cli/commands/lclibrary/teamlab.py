import json

import typer

from sufe_cli.config import load_user_profile
from sufe_cli.utils.network import sufe_get

from .utils import get_today_str, parse_data, validate_reservation

app = typer.Typer(help="SUFE 小组研习室 相关命令")


def _merge_members(input_members: str, user_id: str) -> list[str]:
    """将用户输入的成员列表与当前用户学号合并并去重"""
    member_ids = [m.strip() for m in input_members.split(",") if m.strip()]
    if user_id and user_id not in member_ids:
        member_ids.append(user_id)
    return member_ids


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
    members: str = typer.Argument(
        ..., help="其他成员学号列表, 逗号分隔 (如: 2023xxxxxx,2023yyyyyy)。系统将自动加入当前登录用户并去重"
    ),
    start: str = typer.Argument(..., help="起始时间, 格式为 2026-05-01 10:40"),
    end: str = typer.Argument(..., help="结束时间, 格式为 2026-05-01 13:10"),
):
    """预约小组研习室"""
    # 0. 加载当前用户信息并合并成员列表
    profile = load_user_profile()
    if profile is None or not profile.user_id:
        typer.secho("未找到用户信息，请先运行 `sufe auth` 完成登录。", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    merged_members = _merge_members(members, profile.user_id)

    # 1. 本地规则校验
    try:
        start_dt, end_dt, member_list = validate_reservation(start=start, end=end, members=",".join(merged_members))
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
        "act": "set_resv",
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
