import pytest
import time_machine

from sufe_cli.commands.canvas.assignment import get_assignment_status, render_assignment_detail
from sufe_cli.commands.canvas.utils import html_to_markdown


@pytest.mark.parametrize(
    ("now", "due_at", "unlock_at", "lock_at", "expected"),
    [
        ("2025-12-01T12:00:00+08:00", "2025-12-07T14:00:00Z", None, None, "进行中"),
        ("2025-12-08T12:00:00+08:00", "2025-12-07T14:00:00Z", None, None, "已逾期"),
        ("2025-11-01T12:00:00+08:00", "2025-12-07T14:00:00Z", "2025-12-01T08:00:00Z", None, "未解锁"),
        ("2025-12-01T12:00:00+08:00", "2025-11-30T14:00:00Z", None, "2025-11-29T14:00:00Z", "已锁定"),
    ],
)
def test_assignment_status_priority(
    now: str, due_at: str | None, unlock_at: str | None, lock_at: str | None, expected: str
) -> None:
    with time_machine.travel(now):
        assert get_assignment_status(due_at, unlock_at, lock_at) == expected


def test_render_assignment_detail_uses_status_and_markdown_description() -> None:
    with time_machine.travel("2025-12-01T12:00:00+08:00"):
        output = render_assignment_detail(
            {
                "id": 30662,
                "name": "Homework 2",
                "description": "<p><strong>作业</strong>描述</p>",
                "due_at": "2025-12-07T14:00:00Z",
                "unlock_at": None,
                "lock_at": None,
            }
        )

    assert output == "# Homework 2\n\n**状态**: 进行中\n\n**作业**描述"


@pytest.mark.parametrize(
    ("html", "expected"),
    [
        (
            '<p><a title="hw1.pdf" href="https://canvas.shufe.edu.cn/courses/1/files/123?wrap=1">hw1.pdf</a></p>',
            "[hw1.pdf](file:123)",
        ),
        (
            '<p><img src="https://canvas.shufe.edu.cn/courses/1/files/456/preview" alt="image.png"></p>',
            "[image.png](file:456)",
        ),
        ("<ol><li>First</li><li>Second</li></ol><ul><li>Bullet</li></ul>", "1. First\n1. Second\n\n- Bullet"),
        (
            '<iframe src="https://canvas.shufe.edu.cn/retrieve?fileId=789"></iframe>',
            '<iframe src="https://canvas.shufe.edu.cn/retrieve?fileId=789"></iframe>',
        ),
    ],
)
def test_html_to_markdown_key_canvas_cases(html: str, expected: str) -> None:
    assert html_to_markdown(html) == expected
