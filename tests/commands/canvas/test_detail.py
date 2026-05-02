import pytest
import time_machine

from sufe_cli.commands.canvas.assignment import get_assignment_detail


class DummyResponse:
    def __init__(self, data: dict, status_code: int = 200) -> None:
        self._data = data
        self.status_code = status_code

    def json(self) -> dict:
        return self._data


@time_machine.travel("2025-12-01T12:00:00+08:00")
def test_assignment_status_in_progress(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """测试作业状态：进行中（无限制），验证 Markdown 输出"""
    assignment_data = {
        "id": 30662,
        "name": "Homework 2",
        "description": "<p>作业描述内容</p>",
        "due_at": "2025-12-07T14:00:00Z",
        "unlock_at": None,
        "lock_at": None,
    }

    monkeypatch.setattr(
        "sufe_cli.commands.canvas.assignment.sufe_get_canvas",
        lambda url: DummyResponse(assignment_data),
    )

    get_assignment_detail(course_id=34735, assignment_id=30662)

    captured = capsys.readouterr()
    output = captured.out

    assert "# Homework 2" in output
    assert "**状态**: 进行中" in output
    assert "作业描述内容" in output
    assert "30662" not in output  # 不应包含 id


@time_machine.travel("2025-12-08T12:00:00+08:00")
def test_assignment_status_overdue(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """测试作业状态：已逾期"""
    assignment_data = {
        "id": 30662,
        "name": "Homework 2",
        "description": "<p>作业描述</p>",
        "due_at": "2025-12-07T14:00:00Z",
        "unlock_at": None,
        "lock_at": None,
    }

    monkeypatch.setattr(
        "sufe_cli.commands.canvas.assignment.sufe_get_canvas",
        lambda url: DummyResponse(assignment_data),
    )

    get_assignment_detail(course_id=34735, assignment_id=30662)

    captured = capsys.readouterr()
    assert "**状态**: 已逾期" in captured.out


@time_machine.travel("2025-11-01T12:00:00+08:00")
def test_assignment_status_not_unlocked(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """测试作业状态：未解锁"""
    assignment_data = {
        "id": 30662,
        "name": "Homework 2",
        "description": "<p>作业描述</p>",
        "due_at": "2025-12-07T14:00:00Z",
        "unlock_at": "2025-12-01T08:00:00Z",
        "lock_at": None,
    }

    monkeypatch.setattr(
        "sufe_cli.commands.canvas.assignment.sufe_get_canvas",
        lambda url: DummyResponse(assignment_data),
    )

    get_assignment_detail(course_id=34735, assignment_id=30662)

    captured = capsys.readouterr()
    assert "**状态**: 未解锁" in captured.out


@time_machine.travel("2025-12-10T12:00:00+08:00")
def test_assignment_status_locked(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """测试作业状态：已锁定（优先级最高）"""
    assignment_data = {
        "id": 30662,
        "name": "Homework 2",
        "description": "<p>作业描述</p>",
        "due_at": "2025-12-07T14:00:00Z",
        "unlock_at": "2025-12-01T08:00:00Z",
        "lock_at": "2025-12-09T14:00:00Z",
    }

    monkeypatch.setattr(
        "sufe_cli.commands.canvas.assignment.sufe_get_canvas",
        lambda url: DummyResponse(assignment_data),
    )

    get_assignment_detail(course_id=34735, assignment_id=30662)

    captured = capsys.readouterr()
    assert "**状态**: 已锁定" in captured.out


@time_machine.travel("2025-12-01T12:00:00+08:00")
def test_assignment_status_locked_priority_over_overdue(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """测试已锁定优先级高于已逾期"""
    assignment_data = {
        "id": 30662,
        "name": "Homework 2",
        "description": "<p>作业描述</p>",
        "due_at": "2025-11-30T14:00:00Z",
        "unlock_at": None,
        "lock_at": "2025-11-29T14:00:00Z",
    }

    monkeypatch.setattr(
        "sufe_cli.commands.canvas.assignment.sufe_get_canvas",
        lambda url: DummyResponse(assignment_data),
    )

    get_assignment_detail(course_id=34735, assignment_id=30662)

    captured = capsys.readouterr()
    assert "**状态**: 已锁定" in captured.out


@time_machine.travel("2025-12-01T12:00:00+08:00")
def test_detail_file_links(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """测试文件链接转换为 Markdown"""
    assignment_data = {
        "id": 1,
        "name": "Test Assignment",
        "description": (
            '<p><a class="instructure_file_link" title="hw1.pdf" '
            'href="https://canvas.shufe.edu.cn/courses/1/files/123?wrap=1">hw1.pdf</a></p>'
        ),
        "due_at": None,
        "unlock_at": None,
        "lock_at": None,
    }

    monkeypatch.setattr(
        "sufe_cli.commands.canvas.assignment.sufe_get_canvas",
        lambda url: DummyResponse(assignment_data),
    )

    get_assignment_detail(course_id=1, assignment_id=1)

    captured = capsys.readouterr()
    assert "[hw1.pdf](file:123)" in captured.out


@time_machine.travel("2025-12-01T12:00:00+08:00")
def test_detail_image_links(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """测试图片转换为 Markdown 文件链接"""
    assignment_data = {
        "id": 1,
        "name": "Test Assignment",
        "description": (
            '<p><img src="https://canvas.shufe.edu.cn/courses/1/files/456/preview" '
            'alt="image.png" data-api-endpoint="https://canvas.shufe.edu.cn/api/v1/courses/1/files/456"></p>'
        ),
        "due_at": None,
        "unlock_at": None,
        "lock_at": None,
    }

    monkeypatch.setattr(
        "sufe_cli.commands.canvas.assignment.sufe_get_canvas",
        lambda url: DummyResponse(assignment_data),
    )

    get_assignment_detail(course_id=1, assignment_id=1)

    captured = capsys.readouterr()
    assert "[image.png](file:456)" in captured.out


@time_machine.travel("2025-12-01T12:00:00+08:00")
def test_detail_iframe_preserved(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """测试 iframe 保留原始 HTML"""
    iframe_html = (
        '<iframe src="https://canvas.shufe.edu.cn/courses/1/external_tools/retrieve?fileId=789" '
        'width="640" height="480"></iframe>'
    )
    assignment_data = {
        "id": 1,
        "name": "Test Assignment",
        "description": f"<p>{iframe_html}</p>",
        "due_at": None,
        "unlock_at": None,
        "lock_at": None,
    }

    monkeypatch.setattr(
        "sufe_cli.commands.canvas.assignment.sufe_get_canvas",
        lambda url: DummyResponse(assignment_data),
    )

    get_assignment_detail(course_id=1, assignment_id=1)

    captured = capsys.readouterr()
    assert "<iframe" in captured.out
    assert "fileId=789" in captured.out


@time_machine.travel("2025-12-01T12:00:00+08:00")
def test_detail_unsupported_tag_preserved(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """测试不支持的标签保留原始 HTML"""
    assignment_data = {
        "id": 1,
        "name": "Test Assignment",
        "description": "<p>Some text</p><custom-tag>custom content</custom-tag>",
        "due_at": None,
        "unlock_at": None,
        "lock_at": None,
    }

    monkeypatch.setattr(
        "sufe_cli.commands.canvas.assignment.sufe_get_canvas",
        lambda url: DummyResponse(assignment_data),
    )

    get_assignment_detail(course_id=1, assignment_id=1)

    captured = capsys.readouterr()
    assert "<custom-tag>custom content</custom-tag>" in captured.out


@time_machine.travel("2025-12-01T12:00:00+08:00")
def test_detail_list_conversion(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """测试列表转换为 Markdown"""
    assignment_data = {
        "id": 1,
        "name": "Test Assignment",
        "description": "<ol><li>First item</li><li>Second item</li></ol><ul><li>Bullet 1</li><li>Bullet 2</li></ul>",
        "due_at": None,
        "unlock_at": None,
        "lock_at": None,
    }

    monkeypatch.setattr(
        "sufe_cli.commands.canvas.assignment.sufe_get_canvas",
        lambda url: DummyResponse(assignment_data),
    )

    get_assignment_detail(course_id=1, assignment_id=1)

    captured = capsys.readouterr()
    assert "1. First item" in captured.out
    assert "1. Second item" in captured.out
    assert "- Bullet 1" in captured.out
    assert "- Bullet 2" in captured.out


@time_machine.travel("2025-12-01T12:00:00+08:00")
def test_detail_empty_description(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """测试空描述"""
    assignment_data = {
        "id": 1,
        "name": "Test Assignment",
        "description": "",
        "due_at": None,
        "unlock_at": None,
        "lock_at": None,
    }

    monkeypatch.setattr(
        "sufe_cli.commands.canvas.assignment.sufe_get_canvas",
        lambda url: DummyResponse(assignment_data),
    )

    get_assignment_detail(course_id=1, assignment_id=1)

    captured = capsys.readouterr()
    assert "# Test Assignment" in captured.out
    assert "**状态**: 进行中" in captured.out


@time_machine.travel("2025-12-01T12:00:00+08:00")
def test_detail_formatting_tags(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """测试格式化标签（strong, em, br）"""
    assignment_data = {
        "id": 1,
        "name": "Test Assignment",
        "description": "<p><strong>Bold</strong> and <em>italic</em><br>new line</p>",
        "due_at": None,
        "unlock_at": None,
        "lock_at": None,
    }

    monkeypatch.setattr(
        "sufe_cli.commands.canvas.assignment.sufe_get_canvas",
        lambda url: DummyResponse(assignment_data),
    )

    get_assignment_detail(course_id=1, assignment_id=1)

    captured = capsys.readouterr()
    assert "**Bold**" in captured.out
    assert "*italic*" in captured.out
    assert "new line" in captured.out
