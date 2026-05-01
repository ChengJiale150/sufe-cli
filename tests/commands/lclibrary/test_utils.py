import time_machine

import pytest

from sufe_cli.commands.lclibrary.teamlab import _merge_members
from sufe_cli.commands.lclibrary.utils import (
    StatusEnum,
    get_today_str,
    parse_data,
    validate_reservation,
)


class TestStatusEnum:
    def test_values(self) -> None:
        assert StatusEnum.FREE == "空闲"
        assert StatusEnum.OCCUPIED == "已预约"
        assert StatusEnum.PASSED == "过期"


class TestGetTodayStr:
    @time_machine.travel("2026-05-01T14:30:00+08:00")
    def test_format_and_timezone(self) -> None:
        result = get_today_str()
        assert result == "20260501"


class TestValidateReservation:
    @time_machine.travel("2026-05-01T12:00:00+08:00")
    def test_member_count_too_few(self) -> None:
        with pytest.raises(ValueError, match="预约人数必须在 3 到 10 人之间"):
            validate_reservation("2026-05-01 14:00", "2026-05-01 15:00", "2023001,2023002")

    @time_machine.travel("2026-05-01T12:00:00+08:00")
    def test_member_count_too_many(self) -> None:
        members = ",".join([f"2023{i:04d}" for i in range(1, 12)])
        with pytest.raises(ValueError, match="预约人数必须在 3 到 10 人之间"):
            validate_reservation("2026-05-01 14:00", "2026-05-01 15:00", members)

    @time_machine.travel("2026-05-01T12:00:00+08:00")
    def test_invalid_time_format(self) -> None:
        with pytest.raises(ValueError, match="时间格式错误"):
            validate_reservation("2026/05/01 14:00", "2026-05-01 15:00")

    @time_machine.travel("2026-05-01T12:00:00+08:00")
    def test_minute_not_multiple_of_ten(self) -> None:
        with pytest.raises(ValueError, match="预约时间必须是 10 分钟的整数倍"):
            validate_reservation("2026-05-01 14:05", "2026-05-01 15:00")

    @time_machine.travel("2026-05-01T12:00:00+08:00")
    def test_end_before_start(self) -> None:
        with pytest.raises(ValueError, match="结束时间必须晚于起始时间"):
            validate_reservation("2026-05-01 15:00", "2026-05-01 14:00")

    @time_machine.travel("2026-05-01T12:00:00+08:00")
    def test_duration_too_short(self) -> None:
        with pytest.raises(ValueError, match="预约时长不能少于 1.0 小时"):
            validate_reservation("2026-05-01 14:00", "2026-05-01 14:30")

    @time_machine.travel("2026-05-01T12:00:00+08:00")
    def test_duration_too_long(self) -> None:
        with pytest.raises(ValueError, match="预约时长不能超过 4 小时"):
            validate_reservation("2026-05-01 14:00", "2026-05-01 19:00")

    @time_machine.travel("2026-05-01T12:00:00+08:00")
    def test_past_time(self) -> None:
        with pytest.raises(ValueError, match="不能预约过去的时间"):
            validate_reservation("2026-05-01 10:00", "2026-05-01 11:00")

    @time_machine.travel("2026-05-01T12:00:00+08:00")
    def test_more_than_7_days_ahead(self) -> None:
        with pytest.raises(ValueError, match="最早只能提前 7 天预约"):
            validate_reservation("2026-05-09 14:00", "2026-05-09 15:00")

    @time_machine.travel("2026-05-01T12:00:00+08:00")
    def test_valid_reservation(self) -> None:
        start_dt, end_dt, members = validate_reservation(
            "2026-05-01 14:00", "2026-05-01 16:00", "2023001,2023002,2023003"
        )
        assert start_dt.hour == 14
        assert end_dt.hour == 16
        assert len(members) == 3

    @time_machine.travel("2026-05-01T12:00:00+08:00")
    def test_multimedia_short_duration(self) -> None:
        start_dt, end_dt, members = validate_reservation(
            "2026-05-01 14:00", "2026-05-01 14:10", min_hours=10 / 60, max_hours=3
        )
        assert (end_dt - start_dt).total_seconds() == 600


class TestParseData:
    @time_machine.travel("2026-05-01T12:00:00+08:00")
    def test_basic_parse_and_status(self) -> None:
        json_data = {
            "data": [
                {
                    "devId": "1001",
                    "devName": "Room A",
                    "openStart": "08:00",
                    "openEnd": "22:00",
                    "ts": [{"start": "2026-05-01 10:00", "end": "2026-05-01 12:00"}],
                }
            ]
        }
        result = parse_data(json_data, "20260501")
        assert result["current_time"] == "2026-05-01 12:00"
        teams = result["teams"]
        assert len(teams) == 1
        assert teams[0]["id"] == "1001"
        assert teams[0]["name"] == "Room A"

        periods = teams[0]["periods"]
        # 08:00-10:00 应该是 PASSED (过期，因为 now=12:00)
        assert periods[0]["status"] == StatusEnum.PASSED.value
        # 10:00-12:00 应该是 OCCUPIED (已预约)
        assert periods[1]["status"] == StatusEnum.OCCUPIED.value
        # 12:00-22:00 应该是 FREE (空闲)
        assert periods[2]["status"] == StatusEnum.FREE.value

    @time_machine.travel("2026-05-01T08:00:00+08:00")
    def test_merge_adjacent_same_status(self) -> None:
        json_data = {
            "data": [
                {
                    "devId": "1002",
                    "devName": "Room B",
                    "openStart": "08:00",
                    "openEnd": "22:00",
                    "ts": [],
                }
            ]
        }
        result = parse_data(json_data, "20260501")
        periods = result["teams"][0]["periods"]
        # 没有预约，整段应该是 FREE
        assert len(periods) == 1
        assert periods[0]["period"] == "08:00 - 22:00"
        assert periods[0]["status"] == StatusEnum.FREE.value

    @time_machine.travel("2026-05-01T12:00:00+08:00")
    def test_occupied_time_clipping(self) -> None:
        json_data = {
            "data": [
                {
                    "devId": "1003",
                    "devName": "Room C",
                    "openStart": "08:00",
                    "openEnd": "22:00",
                    "ts": [
                        # 超出开放时间，应该被裁剪到 08:00-22:00
                        {"start": "2026-05-01 06:00", "end": "2026-05-01 10:00"},
                        {"start": "2026-05-01 20:00", "end": "2026-05-01 23:00"},
                    ],
                }
            ]
        }
        result = parse_data(json_data, "20260501")
        periods = result["teams"][0]["periods"]
        # 被裁剪后的 08:00-10:00 和 20:00-22:00 应该是 OCCUPIED
        occupied_periods = [p for p in periods if p["status"] == StatusEnum.OCCUPIED.value]
        assert len(occupied_periods) == 2
        assert occupied_periods[0]["period"] == "08:00 - 10:00"
        assert occupied_periods[1]["period"] == "20:00 - 22:00"

    @time_machine.travel("2026-05-01T14:00:00+08:00")
    def test_split_passed_and_free(self) -> None:
        json_data = {
            "data": [
                {
                    "devId": "1004",
                    "devName": "Room D",
                    "openStart": "08:00",
                    "openEnd": "22:00",
                    "ts": [],
                }
            ]
        }
        result = parse_data(json_data, "20260501")
        periods = result["teams"][0]["periods"]
        # 08:00-14:00 PASSED, 14:00-22:00 FREE
        assert len(periods) == 2
        assert periods[0]["status"] == StatusEnum.PASSED.value
        assert periods[0]["period"] == "08:00 - 14:00"
        assert periods[1]["status"] == StatusEnum.FREE.value
        assert periods[1]["period"] == "14:00 - 22:00"

    @time_machine.travel("2026-05-01T08:00:00+08:00")
    def test_invalid_open_time_fallback(self) -> None:
        json_data = {
            "data": [
                {
                    "devId": "1005",
                    "devName": "Room E",
                    "openStart": "invalid",
                    "openEnd": "invalid",
                    "ts": [],
                }
            ]
        }
        result = parse_data(json_data, "20260501")
        periods = result["teams"][0]["periods"]
        # 应该回退到默认的 08:00-22:00，且整段 FREE
        assert len(periods) == 1
        assert periods[0]["period"] == "08:00 - 22:00"
        assert periods[0]["status"] == StatusEnum.FREE.value


class TestMergeMembers:
    def test_add_current_user_when_not_present(self) -> None:
        result = _merge_members("2023001,2023002", "2023003")
        assert result == ["2023001", "2023002", "2023003"]

    def test_deduplicate_when_user_already_present(self) -> None:
        result = _merge_members("2023001,2023003", "2023003")
        assert result == ["2023001", "2023003"]

    def test_empty_user_id_does_nothing(self) -> None:
        result = _merge_members("2023001,2023002", "")
        assert result == ["2023001", "2023002"]

    def test_empty_members_only_returns_user(self) -> None:
        result = _merge_members("", "2023001")
        assert result == ["2023001"]

    def test_handles_whitespace(self) -> None:
        result = _merge_members(" 2023001 , 2023002 ", "2023003")
        assert result == ["2023001", "2023002", "2023003"]
