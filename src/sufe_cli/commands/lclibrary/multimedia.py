from typing import Annotated

import typer

from sufe_cli.cli_helpers import cli_error_boundary

from .facilities import FacilitySpec, list_facility_status, reserve_facility
from .utils import get_today_str

app = typer.Typer(help="SUFE 多媒体制作室 相关命令")
MULTIMEDIA_SPEC = FacilitySpec(kind_id="100811035", lab_id="115187637", min_hours=10 / 60, max_hours=3)


@app.command(name="list")
@cli_error_boundary
def list_multimedia(
    date: Annotated[str, typer.Argument(default_factory=get_today_str, help="查询日期, 例如20260502, 默认为今天")],
):
    """列出指定日期的多媒体制作室状态"""
    list_facility_status(MULTIMEDIA_SPEC, date)


@app.command(name="reserve")
@cli_error_boundary
def reserve_multimedia(
    id: Annotated[str, typer.Argument(help="预约的多媒体制作室 ID")],
    start: Annotated[str, typer.Argument(help="起始时间, 格式为 2026-05-01 13:40")],
    end: Annotated[str, typer.Argument(help="结束时间, 格式为 2026-05-01 16:00")],
):
    """预约多媒体制作室"""
    reserve_facility(MULTIMEDIA_SPEC, id, start, end)
