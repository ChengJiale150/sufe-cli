import json

import pytest

from sufe_cli.commands.canvas.assignment import list_assignments


def test_merge_assignments_and_submissions(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """测试 assignment 与 submission 的合并逻辑"""
    assignment_data = [
        {
            "id": 19634,
            "name": "作业",
            "assignments": [
                {"id": 30662, "name": "Homework 2", "due_at": "2025-11-02T14:00:00Z", "points_possible": 140},
                {"id": 30663, "name": "Homework 3", "due_at": "2025-11-09T14:00:00Z", "points_possible": 100},
            ],
        }
    ]

    submission_data = [
        {"assignment_id": 30662, "grade": "100", "submitted_at": "2025-10-12T09:47:00Z"},
    ]

    call_count = 0

    def fake_fetch_all_pages(url: str, params: dict | None = None, **kwargs) -> list:
        nonlocal call_count
        call_count += 1
        if "assignment_groups" in url:
            return assignment_data
        return submission_data

    monkeypatch.setattr("sufe_cli.commands.canvas.assignment.fetch_all_pages", fake_fetch_all_pages)

    list_assignments(course_id=34735)

    captured = capsys.readouterr()
    result = json.loads(captured.out)

    assert len(result) == 2

    hw2 = result[0]
    assert hw2["id"] == 30662
    assert hw2["grade"] == "100"
    assert hw2["submitted_at"] == "2025-10-12T09:47:00Z"

    hw3 = result[1]
    assert hw3["id"] == 30663
    assert hw3["grade"] is None
    assert hw3["submitted_at"] is None


def test_merge_with_missing_submissions(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """测试没有 submission 时返回 null"""
    assignment_data = [
        {
            "id": 19634,
            "name": "作业",
            "assignments": [
                {"id": 30662, "name": "Homework 2", "due_at": "2025-11-02T14:00:00Z", "points_possible": 140},
            ],
        }
    ]

    submission_data: list[dict] = []

    def fake_fetch_all_pages(url: str, params: dict | None = None, **kwargs) -> list:
        if "assignment_groups" in url:
            return assignment_data
        return submission_data

    monkeypatch.setattr("sufe_cli.commands.canvas.assignment.fetch_all_pages", fake_fetch_all_pages)

    list_assignments(course_id=34735)

    captured = capsys.readouterr()
    result = json.loads(captured.out)

    assert len(result) == 1
    assert result[0]["grade"] is None
    assert result[0]["submitted_at"] is None
