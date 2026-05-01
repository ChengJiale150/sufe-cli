import json

import typer

from .utils import fetch_all_pages

CANVAS_BASE = "https://canvas.shufe.edu.cn"

app = typer.Typer(help="Canvas 作业相关命令")


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
                    "due_at": assignment.get("due_at"),
                    "points_possible": assignment.get("points_possible"),
                    "grade": sub.get("grade") if sub else None,
                    "submitted_at": sub.get("submitted_at") if sub else None,
                }
            )

    typer.echo(json.dumps(assignments, ensure_ascii=False, indent=2))
