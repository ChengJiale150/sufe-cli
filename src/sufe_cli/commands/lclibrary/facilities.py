import json
from dataclasses import dataclass
from datetime import datetime

import typer

from sufe_cli.errors import InvalidResponseError, SufeCliError

from .client import LCLIBRARY_BASE, sufe_get
from .utils import parse_data, validate_reservation


@dataclass(frozen=True)
class FacilitySpec:
    kind_id: str
    lab_id: str
    min_hours: float = 1.0
    max_hours: int = 4


def list_facility_status(spec: FacilitySpec, date: str) -> None:
    url = f"{LCLIBRARY_BASE}/ClientWeb/pro/ajax/device.aspx?kind_id={spec.kind_id}&date={date}&act=get_rsv_sta"
    data = _read_json_response(sufe_get(url), "解析 JSON 失败")

    if data.get("ret") != 1:
        raise SufeCliError(f"服务器返回错误: {data.get('msg')}")

    try:
        result = parse_data(data, date)
    except Exception as e:
        raise InvalidResponseError(f"处理数据时出错: {e}") from e

    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


def reserve_facility(spec: FacilitySpec, device_id: str, start: str, end: str) -> None:
    start_dt, end_dt = validate_reservation_for_cli(
        start,
        end,
        min_hours=spec.min_hours,
        max_hours=spec.max_hours,
    )
    submit_reservation(
        {
            "dev_id": device_id,
            "lab_id": spec.lab_id,
            "kind_id": spec.kind_id,
            "act": "set_resv",
            "start": start_dt.strftime("%Y-%m-%d %H:%M"),
            "end": end_dt.strftime("%Y-%m-%d %H:%M"),
        }
    )


def validate_reservation_for_cli(
    start: str,
    end: str,
    *,
    members: str | None = None,
    min_hours: float = 1.0,
    max_hours: int = 4,
) -> tuple[datetime, datetime]:
    try:
        start_dt, end_dt, _ = validate_reservation(
            start=start,
            end=end,
            members=members,
            min_hours=min_hours,
            max_hours=max_hours,
        )
    except ValueError as e:
        raise SufeCliError(f"校验失败: {e}") from e
    return start_dt, end_dt


def submit_reservation(params: dict[str, str]) -> None:
    url = f"{LCLIBRARY_BASE}/ClientWeb/pro/ajax/reserve.aspx"
    data = _read_json_response(sufe_get(url, params=params), "解析失败")

    if data.get("ret") == 1:
        typer.secho("✅ 预约成功！", fg=typer.colors.GREEN)
        if data.get("msg") and str(data.get("msg")).lower() != "ok":
            typer.secho(f"服务器返回消息: {data.get('msg')}", fg=typer.colors.YELLOW)
        return

    err_msg = data.get("msg", "未知错误")
    raise SufeCliError(f"❌ 预约失败: {err_msg}")


def _read_json_response(response, failure_message: str) -> dict:
    try:
        data = response.json()
    except Exception as e:
        raise InvalidResponseError(f"{failure_message}: {e}") from e

    if not isinstance(data, dict):
        raise InvalidResponseError("API 返回的数据格式异常，不是预期的对象格式。")
    return data
