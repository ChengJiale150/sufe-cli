from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

TZ_BJ = timezone(timedelta(hours=8))


class StatusEnum(str, Enum):
    FREE = "空闲"
    OCCUPIED = "已预约"
    PASSED = "过期"


def get_today_str() -> str:
    """获取今天日期的字符串格式 (YYYYMMDD, 东八区)"""
    return datetime.now(TZ_BJ).strftime("%Y%m%d")


def parse_data(json_data: dict[str, Any], target_date_str: str) -> dict[str, Any]:
    """
    解析服务器返回的 JSON 数据并进行重组
    target_date_str: 格式为 '20260501'
    """
    now = datetime.now(TZ_BJ)

    target_date = datetime.strptime(target_date_str, "%Y%m%d").date()

    teamlabs = []

    data = json_data.get("data", [])
    if not isinstance(data, list):
        data = []

    for item in data:
        if not isinstance(item, dict):
            continue
        dev_id = item.get("devId")
        dev_name = item.get("devName")

        # 动态解析设施当天的开放起始和结束时间
        open_start_str = item.get("openStart", "08:00")
        open_end_str = item.get("openEnd", "22:00")

        try:
            st_time = datetime.strptime(open_start_str, "%H:%M").time()
            ed_time = datetime.strptime(open_end_str, "%H:%M").time()
        except ValueError:
            st_time = datetime.strptime("08:00", "%H:%M").time()
            ed_time = datetime.strptime("22:00", "%H:%M").time()

        start_of_day = datetime(
            target_date.year, target_date.month, target_date.day, st_time.hour, st_time.minute, tzinfo=TZ_BJ
        )
        end_of_day = datetime(
            target_date.year, target_date.month, target_date.day, ed_time.hour, ed_time.minute, tzinfo=TZ_BJ
        )

        # 解析已经预约的（占据的）时间段
        occupied = []
        time_spans = item.get("ts", [])
        if not isinstance(time_spans, list):
            time_spans = []
        for ts in time_spans:
            if not isinstance(ts, dict):
                continue
            try:
                # API 返回格式：2026-05-01 10:50
                st = datetime.strptime(ts["start"], "%Y-%m-%d %H:%M").replace(tzinfo=TZ_BJ)
                ed = datetime.strptime(ts["end"], "%Y-%m-%d %H:%M").replace(tzinfo=TZ_BJ)

                # 裁剪到 08:00 - 22:00 范围内
                st = max(st, start_of_day)
                ed = min(ed, end_of_day)

                if st < ed:
                    occupied.append((st, ed))
            except (KeyError, ValueError):
                continue

        # 按开始时间排序
        occupied.sort(key=lambda x: x[0])

        # 生成包含空闲和占据的初始段落
        segments = []
        current_time = start_of_day

        for st, ed in occupied:
            if st > current_time:
                segments.append((current_time, st, False))  # False 表示未占据
            if ed > current_time:
                segments.append((max(current_time, st), ed, True))  # True 表示占据
                current_time = ed

        if current_time < end_of_day:
            segments.append((current_time, end_of_day, False))

        # 根据 now 将未占据的时间段切分为过时或空闲
        final_segments = []
        for st, ed, is_occupied in segments:
            if is_occupied:
                final_segments.append((st, ed, StatusEnum.OCCUPIED))
            else:
                if ed <= now:
                    final_segments.append((st, ed, StatusEnum.PASSED))
                elif st >= now:
                    final_segments.append((st, ed, StatusEnum.FREE))
                else:
                    final_segments.append((st, now, StatusEnum.PASSED))
                    final_segments.append((now, ed, StatusEnum.FREE))

        # 合并相邻且状态相同的时间段
        merged: list[tuple[datetime, datetime, StatusEnum]] = []
        for seg in final_segments:
            if not merged:
                merged.append(seg)
            else:
                last_st, last_ed, last_status = merged[-1]
                if last_status == seg[2] and last_ed == seg[0]:
                    merged[-1] = (last_st, seg[1], last_status)
                else:
                    merged.append(seg)

        # 格式化输出
        periods = []
        for st, ed, status in merged:
            st_str = st.strftime("%H:%M")
            ed_str = ed.strftime("%H:%M")
            periods.append({"period": f"{st_str} - {ed_str}", "status": status.value})

        teamlabs.append({"id": dev_id, "name": dev_name, "periods": periods})

    return {"current_time": now.strftime("%Y-%m-%d %H:%M"), "teams": teamlabs}


def validate_reservation(
    start: str, end: str, members: str | None = None, min_hours: float = 1.0, max_hours: int = 4
) -> tuple[datetime, datetime, list[str]]:
    """
    校验预约规则
    返回解析后的 (start_dt, end_dt, member_list)
    若校验失败抛出 ValueError
    """
    # 1. 校验人数 (仅当提供了 members 时校验 3-10 人)
    member_list = []
    if members is not None:
        member_list = [m.strip() for m in members.split(",") if m.strip()]
        if not (3 <= len(member_list) <= 10):
            raise ValueError(f"预约人数必须在 3 到 10 人之间，当前输入 {len(member_list)} 人")

    # 2. 时间格式解析
    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M").replace(tzinfo=TZ_BJ)
        end_dt = datetime.strptime(end, "%Y-%m-%d %H:%M").replace(tzinfo=TZ_BJ)
    except ValueError:
        raise ValueError("时间格式错误，请使用 'YYYY-MM-DD HH:MM'，如 '2026-05-01 10:40'")

    # 3. 校验分钟颗粒度 (只能为整10分)
    if start_dt.minute % 10 != 0 or end_dt.minute % 10 != 0:
        raise ValueError("预约时间必须是 10 分钟的整数倍，不能精确到分钟，如 '10:40'")

    # 4. 校验时序
    if start_dt >= end_dt:
        raise ValueError("结束时间必须晚于起始时间")

    # 5. 校验时长 (min_hours - max_hours小时)
    duration_seconds = (end_dt - start_dt).total_seconds()
    if duration_seconds < min_hours * 3600:
        if min_hours < 1:
            raise ValueError(f"预约时长不能少于 {int(min_hours * 60)} 分钟")
        else:
            raise ValueError(f"预约时长不能少于 {min_hours} 小时")
    if duration_seconds > max_hours * 3600:
        raise ValueError(f"预约时长不能超过 {max_hours} 小时")

    # 6. 校验提前天数与过去时间
    now = datetime.now(TZ_BJ)
    if start_dt < now:
        raise ValueError("不能预约过去的时间")

    # 提前7天限制（按日期计算，允许预约第7天）
    max_allow_date = (now + timedelta(days=7)).date()
    if start_dt.date() > max_allow_date:
        raise ValueError("最早只能提前 7 天预约")

    return start_dt, end_dt, member_list
