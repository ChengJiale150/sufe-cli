import json
from datetime import datetime

import typer
from zoneinfo import ZoneInfo

from sufe_cli.client.http import sufe_get_canvas
from .utils import fetch_all_pages, html_to_markdown, utc_to_local

CANVAS_BASE = "https://canvas.shufe.edu.cn"

app = typer.Typer(help="Canvas 作业相关命令")


def _get_assignment_status(due_at: str | None, unlock_at: str | None, lock_at: str | None) -> str:
    """判定作业状态，优先级：已锁定 > 未解锁 > 已逾期 > 进行中"""
    now = datetime.now(ZoneInfo("Asia/Shanghai"))

    if lock_at:
        lock_dt = datetime.fromisoformat(lock_at.replace("Z", "+00:00")).astimezone(ZoneInfo("Asia/Shanghai"))
        if now > lock_dt:
            return "已锁定"

    if unlock_at:
        unlock_dt = datetime.fromisoformat(unlock_at.replace("Z", "+00:00")).astimezone(ZoneInfo("Asia/Shanghai"))
        if now < unlock_dt:
            return "未解锁"

    if due_at:
        due_dt = datetime.fromisoformat(due_at.replace("Z", "+00:00")).astimezone(ZoneInfo("Asia/Shanghai"))
        if now > due_dt:
            return "已逾期"

    return "进行中"


@app.command(name="list")
def list_assignments(
    course_id: int = typer.Option(..., "--course-id", help="课程 ID"),
):
    """列出指定课程的作业及提交状态"""
    assignments_url = (
        f"{CANVAS_BASE}/api/v1/courses/{course_id}/assignment_groups"
        f"?include[]=assignments&exclude_response_fields[]=description"
    )
    submissions_url = f"{CANVAS_BASE}/api/v1/courses/{course_id}/students/submissions?student_ids[]=self"

    assignment_groups = fetch_all_pages(assignments_url)
    submissions = fetch_all_pages(submissions_url)

    submission_map = {}
    for sub in submissions:
        if isinstance(sub, dict) and "assignment_id" in sub:
            submission_map[sub["assignment_id"]] = sub

    assignments = []
    for group in assignment_groups:
        if not isinstance(group, dict):
            continue
        for assignment in group.get("assignments", []):
            if not isinstance(assignment, dict):
                continue
            aid = assignment.get("id")
            sub = submission_map.get(aid)
            assignments.append(
                {
                    "id": aid,
                    "name": assignment.get("name"),
                    "due_at": utc_to_local(assignment.get("due_at")),
                    "points_possible": assignment.get("points_possible"),
                    "grade": sub.get("grade") if sub else None,
                    "submitted_at": utc_to_local(sub.get("submitted_at")) if sub else None,
                }
            )

    typer.echo(json.dumps(assignments, ensure_ascii=False, indent=2))


@app.command(name="detail")
def get_assignment_detail(
    course_id: int = typer.Option(..., "--course-id", help="课程 ID"),
    assignment_id: int = typer.Option(..., "--assignment-id", help="作业 ID"),
):
    """获取指定作业的详情及状态"""
    url = f"{CANVAS_BASE}/api/v1/courses/{course_id}/assignments/{assignment_id}"
    response = sufe_get_canvas(url)

    try:
        data = response.json()
    except Exception as e:
        typer.secho(f"解析 JSON 失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    if not isinstance(data, dict):
        typer.secho("API 返回的数据格式异常，不是预期的对象格式。", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    status = _get_assignment_status(
        data.get("due_at"),
        data.get("unlock_at"),
        data.get("lock_at"),
    )

    description_md = html_to_markdown(data.get("description", ""))

    output = f"# {data.get('name')}\n\n**状态**: {status}\n\n{description_md}"
    typer.echo(output)
