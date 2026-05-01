import json
from typing import Literal

import typer

from sufe_cli.client.http import sufe_get_canvas
from .utils import fetch_all_pages

CANVAS_BASE = "https://canvas.shufe.edu.cn"

SortField = Literal["course_name", "created_at"]
SortOrder = Literal["asc", "desc"]

app = typer.Typer(help="Canvas 课程相关命令")


def _extract_course(course: dict) -> dict:
    """统一提取课程字段"""
    roles = [e.get("role") for e in course.get("enrollments", []) if e.get("role")]
    return {
        "id": course.get("id"),
        "name": course.get("name"),
        "workflow_state": course.get("workflow_state"),
        "created_at": course.get("created_at"),
        "roles": roles,
    }


@app.command(name="list")
def list_courses():
    """列出用户收藏的课程"""
    url = f"{CANVAS_BASE}/api/v1/users/self/favorites/courses"
    response = sufe_get_canvas(url)

    try:
        data = response.json()
    except Exception as e:
        typer.secho(f"解析 JSON 失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    if not isinstance(data, list):
        typer.secho("API 返回的数据格式异常，不是预期的列表格式。", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    courses = [_extract_course(c) for c in data]
    typer.echo(json.dumps(courses, ensure_ascii=False, indent=2))


@app.command(name="all")
def list_all_courses(
    sort: SortField = typer.Option("course_name", "--sort", help="排序字段"),
    order: SortOrder = typer.Option("asc", "--order", help="排序方向"),
    limit: int = typer.Option(20, "--limit", help="返回结果数量限制", min=1),
    offset: int = typer.Option(0, "--offset", help="结果偏移量", min=0),
):
    """列出用户参与的所有课程"""
    url = f"{CANVAS_BASE}/api/v1/courses"
    params = {
        "per_page": 100,
        "sort": sort,
        "order": order,
    }

    data = fetch_all_pages(url, params=params)
    courses = [_extract_course(c) for c in data]

    # 本地排序（Canvas API 排序不可靠）
    reverse = order == "desc"
    if sort == "course_name":
        courses.sort(key=lambda c: c.get("name") or "", reverse=reverse)
    elif sort == "created_at":
        courses.sort(key=lambda c: c.get("created_at") or "", reverse=reverse)

    # 截取结果
    sliced = courses[offset : offset + limit]
    typer.echo(json.dumps(sliced, ensure_ascii=False, indent=2))
