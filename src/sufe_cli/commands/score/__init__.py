from typing import Annotated

import typer

from sufe_cli.cli_helpers import cli_error_boundary
from sufe_cli.client.auth.browser import BrowserAuthError, fetch_page_with_state
from sufe_cli.errors import AuthExpiredError, InvalidResponseError

from .utils import parse_courses, parse_summary, print_tsv

GRADE_URL = "https://eams.sufe.edu.cn/eams/teach/grade/course/person!historyCourseGrade.action?projectType=MAJOR"

SemesterOption = Annotated[str | None, typer.Option("--semester", "-s", help="筛选特定学期，如 '2025-2026 1'")]

app = typer.Typer(help="SUFE 成绩查询相关命令")


def fetch_grade_page() -> str:
    """使用 Playwright 获取成绩页面 HTML 内容。"""
    try:
        return fetch_page_with_state(GRADE_URL)
    except BrowserAuthError as e:
        raise AuthExpiredError(str(e)) from e


@app.command(name="list")
@cli_error_boundary
def list_scores(
    semester: SemesterOption = None,
) -> None:
    """获取全部学科成绩（TSV 格式），可指定学期筛选。"""
    html = fetch_grade_page()
    headers, rows = parse_courses(html)
    if not rows:
        raise InvalidResponseError("未解析到成绩数据，请检查页面内容。")

    if semester:
        rows = [r for r in rows if r[0] == semester]
        if not rows:
            raise InvalidResponseError(f"未找到学期 '{semester}' 的成绩数据。")

    print_tsv(headers, rows)


@app.command()
@cli_error_boundary
def summary() -> None:
    """获取学期总成绩汇总（TSV 格式）。"""
    html = fetch_grade_page()
    headers, rows = parse_summary(html)
    if not rows:
        raise InvalidResponseError("未解析到汇总数据，请检查页面内容。")
    print_tsv(headers, rows)
