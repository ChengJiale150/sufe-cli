import typer

from sufe_cli.client.browser import BrowserAuthError, fetch_page_with_state

GRADE_URL = "https://eams.sufe.edu.cn/eams/teach/grade/course/person!historyCourseGrade.action?projectType=MAJOR"


def fetch_grade_page() -> str:
    """使用 Playwright 获取成绩页面 HTML 内容。"""
    try:
        return fetch_page_with_state(GRADE_URL)
    except BrowserAuthError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
