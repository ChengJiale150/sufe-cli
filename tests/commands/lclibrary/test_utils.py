import pytest
import time_machine

from sufe_cli.commands.lclibrary.teamlab import _merge_members
from sufe_cli.commands.lclibrary.utils import StatusEnum, get_today_str, parse_data, validate_reservation


@time_machine.travel("2026-05-01T14:30:00+08:00")
def test_get_today_str_uses_beijing_date() -> None:
    assert get_today_str() == "20260501"


@pytest.mark.parametrize(
    ("start", "end", "members", "kwargs", "message"),
    [
        ("2026-05-01 14:00", "2026-05-01 15:00", "2023001,2023002", {}, "预约人数必须在 3 到 10 人之间"),
        ("2026/05/01 14:00", "2026-05-01 15:00", None, {}, "时间格式错误"),
        ("2026-05-01 14:05", "2026-05-01 15:00", None, {}, "预约时间必须是 10 分钟的整数倍"),
        ("2026-05-01 15:00", "2026-05-01 14:00", None, {}, "结束时间必须晚于起始时间"),
        ("2026-05-01 14:00", "2026-05-01 14:30", None, {}, "预约时长不能少于 1.0 小时"),
        ("2026-05-01 14:00", "2026-05-01 19:00", None, {}, "预约时长不能超过 4 小时"),
        ("2026-05-01 10:00", "2026-05-01 11:00", None, {}, "不能预约过去的时间"),
        ("2026-05-09 14:00", "2026-05-09 15:00", None, {}, "最早只能提前 7 天预约"),
    ],
)
@time_machine.travel("2026-05-01T12:00:00+08:00")
def test_validate_reservation_rejects_invalid_rules(
    start: str, end: str, members: str | None, kwargs: dict, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_reservation(start, end, members, **kwargs)


@pytest.mark.parametrize(
    ("start", "end", "members", "kwargs", "expected_seconds"),
    [
        ("2026-05-01 14:00", "2026-05-01 16:00", "2023001,2023002,2023003", {}, 7200),
        ("2026-05-01 14:00", "2026-05-01 14:10", None, {"min_hours": 10 / 60, "max_hours": 3}, 600),
    ],
)
@time_machine.travel("2026-05-01T12:00:00+08:00")
def test_validate_reservation_accepts_supported_facility_rules(
    start: str, end: str, members: str | None, kwargs: dict, expected_seconds: int
) -> None:
    start_dt, end_dt, member_list = validate_reservation(start, end, members, **kwargs)

    assert (end_dt - start_dt).total_seconds() == expected_seconds
    if members:
        assert member_list == ["2023001", "2023002", "2023003"]


@time_machine.travel("2026-05-01T12:00:00+08:00")
def test_parse_data_splits_passed_occupied_and_free_periods() -> None:
    result = parse_data(
        {
            "data": [
                {
                    "devId": "1001",
                    "devName": "Room A",
                    "openStart": "08:00",
                    "openEnd": "22:00",
                    "ts": [{"start": "2026-05-01 10:00", "end": "2026-05-01 12:00"}],
                }
            ]
        },
        "20260501",
    )

    assert result["current_time"] == "2026-05-01 12:00"
    assert result["teams"][0]["periods"] == [
        {"period": "08:00 - 10:00", "status": StatusEnum.PASSED.value},
        {"period": "10:00 - 12:00", "status": StatusEnum.OCCUPIED.value},
        {"period": "12:00 - 22:00", "status": StatusEnum.FREE.value},
    ]


@time_machine.travel("2026-05-01T12:00:00+08:00")
def test_parse_data_clips_occupied_periods_to_open_hours() -> None:
    result = parse_data(
        {
            "data": [
                {
                    "devId": "1003",
                    "devName": "Room C",
                    "openStart": "08:00",
                    "openEnd": "22:00",
                    "ts": [
                        {"start": "2026-05-01 06:00", "end": "2026-05-01 10:00"},
                        {"start": "2026-05-01 20:00", "end": "2026-05-01 23:00"},
                    ],
                }
            ]
        },
        "20260501",
    )

    occupied = [p for p in result["teams"][0]["periods"] if p["status"] == StatusEnum.OCCUPIED.value]
    assert occupied == [
        {"period": "08:00 - 10:00", "status": StatusEnum.OCCUPIED.value},
        {"period": "20:00 - 22:00", "status": StatusEnum.OCCUPIED.value},
    ]


@time_machine.travel("2026-05-01T08:00:00+08:00")
def test_parse_data_falls_back_to_default_open_hours() -> None:
    result = parse_data(
        {"data": [{"devId": "1005", "devName": "Room E", "openStart": "invalid", "openEnd": "invalid", "ts": []}]},
        "20260501",
    )

    assert result["teams"][0]["periods"] == [{"period": "08:00 - 22:00", "status": StatusEnum.FREE.value}]


def test_merge_members_strips_and_adds_current_user_once() -> None:
    assert _merge_members(" 2023001 , 2023002,2023003 ", "2023003") == ["2023001", "2023002", "2023003"]
