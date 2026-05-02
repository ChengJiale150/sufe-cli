from typing import Annotated

import typer

from sufe_cli.cli_helpers import cli_error_boundary
from sufe_cli.client.portal import ensure_user_profile

from .facilities import FacilitySpec, list_facility_status, submit_reservation, validate_reservation_for_cli
from .utils import get_today_str

app = typer.Typer(help="SUFE 小组研习室 相关命令")
TEAMLAB_SPEC = FacilitySpec(kind_id="100811029", lab_id="100811022")
ReservationNameArgument = Annotated[str, typer.Argument(help="预约名称")]


def _merge_members(input_members: str, user_id: str) -> list[str]:
    """将用户输入的成员列表与当前用户学号合并并去重"""
    member_ids = [m.strip() for m in input_members.split(",") if m.strip()]
    if user_id and user_id not in member_ids:
        member_ids.append(user_id)
    return member_ids


@app.command(name="list")
@cli_error_boundary
def list_teamlab(
    date: Annotated[str, typer.Argument(default_factory=get_today_str, help="查询日期, 例如20260501, 默认为今天")],
):
    """列出指定日期的小组研习室状态"""
    list_facility_status(TEAMLAB_SPEC, date)


@app.command(name="reserve")
@cli_error_boundary
def reserve_teamlab(
    id: Annotated[str, typer.Argument(help="预约的研讨室 ID")],
    name: ReservationNameArgument,
    members: Annotated[
        str,
        typer.Argument(help="其他成员学号列表, 逗号分隔 (如: 2023xxxxxx,2023yyyyyy)。系统将自动加入当前登录用户并去重"),
    ],
    start: Annotated[str, typer.Argument(help="起始时间, 格式为 2026-05-01 10:40")],
    end: Annotated[str, typer.Argument(help="结束时间, 格式为 2026-05-01 13:10")],
):
    """预约小组研习室"""
    profile = ensure_user_profile()
    merged_members = _merge_members(members, profile.user_id)
    start_dt, end_dt = validate_reservation_for_cli(start=start, end=end, members=",".join(merged_members))

    params = {
        "dev_id": id,
        "lab_id": TEAMLAB_SPEC.lab_id,
        "kind_id": TEAMLAB_SPEC.kind_id,
        "type": "dev",
        "term": "",
        "test_name": name,
        "min_user": "3",
        "max_user": "10",
        "mb_list": ",".join(merged_members),
        "start": start_dt.strftime("%Y-%m-%d %H:%M"),
        "end": end_dt.strftime("%Y-%m-%d %H:%M"),
        "act": "set_resv",
    }

    submit_reservation(params)
