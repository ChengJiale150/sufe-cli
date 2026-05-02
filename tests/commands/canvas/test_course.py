import json

import pytest

from sufe_cli.commands.canvas.course import list_all_courses, list_courses


class DummyResponse:
    def __init__(self, data: list, status_code: int = 200, headers: dict | None = None) -> None:
        self._data = data
        self.status_code = status_code
        self.headers = headers or {}

    def json(self) -> list:
        return self._data


def test_list_courses_output_format(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """测试 list 命令输出统一格式"""
    course_data = [
        {
            "id": 40442,
            "name": "深度学习（0875）",
            "workflow_state": "available",
            "created_at": "2026-02-25T04:03:12Z",
            "enrollments": [{"type": "ta", "role": "TaEnrollment", "user_id": 53509}],
        }
    ]

    monkeypatch.setattr(
        "sufe_cli.commands.canvas.course.sufe_get_canvas",
        lambda url: DummyResponse(course_data),
    )

    list_courses()

    captured = capsys.readouterr()
    result = json.loads(captured.out)

    assert len(result) == 1
    course = result[0]
    assert course["id"] == 40442
    assert course["name"] == "深度学习（0875）"
    assert course["workflow_state"] == "available"
    # UTC 2026-02-25T04:03:12Z => 东八区 2026-02-25 12:03
    assert course["created_at"] == "2026-02-25 12:03"
    assert course["roles"] == ["TaEnrollment"]


def test_list_all_courses(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """测试 all 命令获取所有课程"""
    course_data = [
        {
            "id": 40442,
            "name": "深度学习（0875）",
            "workflow_state": "available",
            "created_at": "2026-02-25T04:03:12Z",
            "enrollments": [{"role": "TaEnrollment"}],
        },
        {
            "id": 40443,
            "name": "机器学习",
            "workflow_state": "completed",
            "created_at": "2025-09-01T08:00:00Z",
            "enrollments": [{"role": "StudentEnrollment"}],
        },
    ]

    def fake_fetch_all_pages(url: str, params: dict | None = None) -> list:
        return course_data

    monkeypatch.setattr("sufe_cli.commands.canvas.course.fetch_all_pages", fake_fetch_all_pages)

    list_all_courses(sort="course_name", order="asc", limit=20, offset=0)

    captured = capsys.readouterr()
    result = json.loads(captured.out)

    assert len(result) == 2
    # 按 course_name 升序排列: 机器学习 < 深度学习
    assert result[0]["id"] == 40443
    assert result[0]["roles"] == ["StudentEnrollment"]
    assert result[1]["id"] == 40442
    assert result[1]["workflow_state"] == "available"
    assert result[1]["roles"] == ["TaEnrollment"]


def test_list_all_courses_sort_by_created_at_desc(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """测试 all 命令按 created_at 降序排序"""
    course_data = [
        {
            "id": 40443,
            "name": "机器学习",
            "workflow_state": "completed",
            "created_at": "2025-09-01T08:00:00Z",
            "enrollments": [{"role": "StudentEnrollment"}],
        },
        {
            "id": 40442,
            "name": "深度学习（0875）",
            "workflow_state": "available",
            "created_at": "2026-02-25T04:03:12Z",
            "enrollments": [{"role": "TaEnrollment"}],
        },
    ]

    def fake_fetch_all_pages(url: str, params: dict | None = None) -> list:
        return course_data

    monkeypatch.setattr("sufe_cli.commands.canvas.course.fetch_all_pages", fake_fetch_all_pages)

    list_all_courses(sort="created_at", order="desc", limit=20, offset=0)

    captured = capsys.readouterr()
    result = json.loads(captured.out)

    assert len(result) == 2
    # 降序：2026-02-25 应在前面
    assert result[0]["id"] == 40442
    assert result[1]["id"] == 40443


def test_list_all_courses_limit_and_offset(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """测试 all 命令 limit 和 offset 截取"""
    course_data = [
        {
            "id": i,
            "name": f"课程{i}",
            "workflow_state": "available",
            "created_at": f"2026-01-{i:02d}T00:00:00Z",
            "enrollments": [],
        }
        for i in range(1, 6)
    ]

    def fake_fetch_all_pages(url: str, params: dict | None = None) -> list:
        return course_data

    monkeypatch.setattr("sufe_cli.commands.canvas.course.fetch_all_pages", fake_fetch_all_pages)

    list_all_courses(sort="course_name", order="asc", limit=2, offset=1)

    captured = capsys.readouterr()
    result = json.loads(captured.out)

    assert len(result) == 2
    assert result[0]["id"] == 2
    assert result[1]["id"] == 3


def test_list_courses_empty_enrollments(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """测试 enrollments 为空时 roles 返回空数组"""
    course_data = [
        {
            "id": 40442,
            "name": "深度学习（0875）",
            "workflow_state": "available",
            "created_at": "2026-02-25T04:03:12Z",
            "enrollments": [],
        }
    ]

    monkeypatch.setattr(
        "sufe_cli.commands.canvas.course.sufe_get_canvas",
        lambda url: DummyResponse(course_data),
    )

    list_courses()

    captured = capsys.readouterr()
    result = json.loads(captured.out)

    assert result[0]["roles"] == []
