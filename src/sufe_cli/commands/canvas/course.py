import json
from typing import Annotated, Literal

import typer

from sufe_cli.cli_helpers import cli_error_boundary
from sufe_cli.errors import InvalidResponseError

from .client import CANVAS_BASE, sufe_get_canvas
from .utils import fetch_all_pages, utc_to_local

SortField = Literal["course_name", "created_at"]
SortOrder = Literal["asc", "desc"]
SortFieldOption = Annotated[SortField, typer.Option("--sort", help="排序字段")]
SortOrderOption = Annotated[SortOrder, typer.Option("--order", help="排序方向")]
LimitOption = Annotated[int, typer.Option("--limit", min=1, help="返回结果数量限制")]
OffsetOption = Annotated[int, typer.Option("--offset", min=0, help="结果偏移量")]

app = typer.Typer(help="Canvas 课程相关命令")


def extract_course(course: dict) -> dict:
    """统一提取课程字段"""
    roles = [e.get("role") for e in course.get("enrollments", []) if e.get("role")]
    return {
        "id": course.get("id"),
        "name": course.get("name"),
        "workflow_state": course.get("workflow_state"),
        "created_at": utc_to_local(course.get("created_at")),
        "roles": roles,
    }


def sort_and_slice_courses(
    courses: list[dict], sort: SortField, order: SortOrder, limit: int, offset: int
) -> list[dict]:
    reverse = order == "desc"
    if sort == "course_name":
        courses.sort(key=lambda c: c.get("name") or "", reverse=reverse)
    elif sort == "created_at":
        courses.sort(key=lambda c: c.get("created_at") or "", reverse=reverse)
    return courses[offset : offset + limit]


@app.command(name="list")
@cli_error_boundary
def list_courses():
    """列出用户收藏的课程"""
    url = f"{CANVAS_BASE}/api/v1/users/self/favorites/courses"
    response = sufe_get_canvas(url)

    try:
        data = response.json()
    except (json.JSONDecodeError, TypeError) as e:
        raise InvalidResponseError(f"解析 JSON 失败: {e}") from e

    if not isinstance(data, list):
        raise InvalidResponseError("API 返回的数据格式异常，不是预期的列表格式。")

    courses = [extract_course(c) for c in data]
    typer.echo(json.dumps(courses, ensure_ascii=False, indent=2))


@app.command(name="all")
@cli_error_boundary
def list_all_courses(
    sort: SortFieldOption = "course_name",
    order: SortOrderOption = "asc",
    limit: LimitOption = 20,
    offset: OffsetOption = 0,
):
    """列出用户参与的所有课程"""
    url = f"{CANVAS_BASE}/api/v1/courses"
    params = {
        "per_page": 100,
        "sort": sort,
        "order": order,
    }

    data = fetch_all_pages(url, params=params)
    courses = [extract_course(c) for c in data]
    typer.echo(json.dumps(sort_and_slice_courses(courses, sort, order, limit, offset), ensure_ascii=False, indent=2))
