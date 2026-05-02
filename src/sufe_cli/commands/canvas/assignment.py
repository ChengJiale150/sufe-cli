import json
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
import typer
from zoneinfo import ZoneInfo

from sufe_cli.client.http import sufe_get_canvas, sufe_post_canvas
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


def _upload_single_file(course_id: int, assignment_id: int, file_path: Path, assignment_page: str) -> dict:
    """上传单个文件到 Canvas 作业，返回文件元数据字典"""
    file_name = file_path.name
    file_size = file_path.stat().st_size
    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"

    # Step 1: 通知 Canvas 即将上传文件
    step1_url = f"{CANVAS_BASE}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/self/files"
    step1_data = {
        "name": file_name,
        "size": str(file_size),
        "content_type": content_type,
    }

    response = sufe_post_canvas(step1_url, data=step1_data, use_auth_token=True, page_url=assignment_page)
    try:
        upload_info = response.json()
    except Exception as e:
        typer.secho(f"解析上传响应失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    if not isinstance(upload_info, dict):
        typer.secho("上传响应格式异常", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    upload_url = upload_info.get("upload_url")
    upload_params = upload_info.get("upload_params")

    if not upload_url or not upload_params:
        errors = upload_info.get("errors", [])
        if errors:
            error_msg = errors[0].get("message", str(errors[0])) if isinstance(errors[0], dict) else str(errors[0])
            typer.secho(f"上传准备失败: {error_msg}", fg=typer.colors.RED, err=True)
        else:
            typer.secho("上传准备失败: 无法获取上传地址", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    # Step 2: 上传文件到 upload_url（手动构建 multipart，避免 requests files 参数导致签名失效）
    try:
        from urllib3.filepost import encode_multipart_formdata

        fields = []
        for key, value in upload_params.items():
            fields.append((key, value))
        with file_path.open("rb") as f:
            content = f.read()
        fields.append(("file", (file_name, content, content_type)))
        body, multipart_content_type = encode_multipart_formdata(fields)
        step2_headers = {
            "Content-Type": multipart_content_type,
            "Content-Length": str(len(body)),
        }
        step2_response = requests.post(upload_url, data=body, headers=step2_headers, allow_redirects=False, timeout=60)
    except requests.RequestException as e:
        typer.secho(f"文件上传失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    # Step 3: 跟随重定向确认上传
    if step2_response.status_code in (301, 302, 303, 307, 308):
        location = step2_response.headers.get("Location")
        if not location:
            typer.secho("上传后未返回重定向地址", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)
        confirm_response = sufe_get_canvas(location)
    elif step2_response.status_code == 201:
        location = step2_response.headers.get("Location")
        if location:
            confirm_response = sufe_get_canvas(location)
        else:
            # 201 Created 且 body 包含文件信息
            confirm_response = step2_response
    else:
        typer.secho(f"文件上传失败 (HTTP {step2_response.status_code})", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    try:
        file_data = confirm_response.json()
    except Exception as e:
        typer.secho(f"解析文件确认响应失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    if not isinstance(file_data, dict) or "id" not in file_data:
        typer.secho("文件上传确认响应格式异常", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    return file_data


@app.command(name="submit")
def submit_assignment(
    course_id: int = typer.Option(..., "--course-id", help="课程 ID"),
    assignment_id: int = typer.Option(..., "--assignment-id", help="作业 ID"),
    files: list[Path] = typer.Option(..., "--file", help="要上传的文件，可多次指定"),
    comment: str | None = typer.Option(None, "--comment", help="提交评论"),
):
    """上传文件并提交 Canvas 作业"""
    # 验证文件存在
    for f in files:
        if not f.exists():
            typer.secho(f"文件不存在: {f}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

    # 获取作业页面 URL（用于 CSRF Token 提取）
    assignment_page = f"{CANVAS_BASE}/courses/{course_id}/assignments/{assignment_id}"

    # 上传所有文件
    uploaded_files: list[dict] = []
    for file_path in files:
        typer.secho(f"正在上传 {file_path.name}...", nl=False, err=True)
        file_data = _upload_single_file(course_id, assignment_id, file_path, assignment_page)
        uploaded_files.append(file_data)
        typer.secho(" 完成", err=True)

    # 提交作业
    submit_url = f"{CANVAS_BASE}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions"
    submit_data: dict[str, Any] = {
        "submission[submission_type]": "online_upload",
    }
    file_ids: list[str] = [str(f["id"]) for f in uploaded_files]
    submit_data["submission[file_ids][]"] = file_ids
    if comment:
        submit_data["comment[text_comment]"] = comment

    response = sufe_post_canvas(submit_url, data=submit_data, use_auth_token=True, page_url=assignment_page)

    try:
        submission = response.json()
    except Exception as e:
        typer.secho(f"解析提交响应失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    if not isinstance(submission, dict):
        typer.secho("提交响应格式异常", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    # 输出文本结果
    lines = [
        "作业提交成功",
        f"尝试次数: {submission.get('attempt', 1)}",
        f"提交时间: {utc_to_local(submission.get('submitted_at')) or '未知'}",
        f"状态: {'已逾期' if submission.get('late') else '正常'}",
        f"文件 ({len(uploaded_files)} 个):",
    ]
    for file_info in uploaded_files:
        fname = file_info.get("display_name") or file_info.get("filename", "未知")
        fsize = file_info.get("size", 0)
        lines.append(f"  - {fname} ({fsize} bytes)")
    if comment:
        lines.append(f"评论: {comment}")

    typer.echo("\n".join(lines))
