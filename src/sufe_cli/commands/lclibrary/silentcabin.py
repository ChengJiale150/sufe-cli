from typing import Annotated

import typer

from sufe_cli.cli_helpers import cli_error_boundary

from .facilities import FacilitySpec, list_facility_status, reserve_facility
from .utils import get_today_str

app = typer.Typer(help="SUFE 静音舱 相关命令")
SILENTCABIN_SPEC = FacilitySpec(kind_id="126386594", lab_id="126386596")


@app.command(name="list")
@cli_error_boundary
def list_silentcabin(
    date: Annotated[str, typer.Argument(default_factory=get_today_str, help="查询日期, 例如20260430, 默认为今天")],
):
    """列出指定日期的静音舱状态"""
    list_facility_status(SILENTCABIN_SPEC, date)


@app.command(name="reserve")
@cli_error_boundary
def reserve_silentcabin(
    id: Annotated[str, typer.Argument(help="预约的静音舱 ID")],
    start: Annotated[str, typer.Argument(help="起始时间, 格式为 2026-05-01 13:40")],
    end: Annotated[str, typer.Argument(help="结束时间, 格式为 2026-05-01 17:40")],
):
    """预约静音舱"""
    reserve_facility(SILENTCABIN_SPEC, id, start, end)
