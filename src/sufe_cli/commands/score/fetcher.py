import typer
from playwright.sync_api import sync_playwright

from sufe_cli.config import STATE_FILE_PATH

GRADE_URL = "https://eams.sufe.edu.cn/eams/teach/grade/course/person!historyCourseGrade.action?projectType=MAJOR"


def fetch_grade_page() -> str:
    """使用 Playwright 获取成绩页面 HTML 内容。"""
    if not STATE_FILE_PATH.exists():
        typer.secho(
            "未找到登录状态文件，请先运行 `sufe auth` 完成登录。",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(STATE_FILE_PATH))
        page = context.new_page()

        page.goto(GRADE_URL)
        page.wait_for_load_state("networkidle")

        if "login.sufe.edu.cn" in page.url:
            typer.secho(
                "登录状态已过期，请运行 `sufe auth` 重新登录。",
                fg=typer.colors.RED,
                err=True,
            )
            browser.close()
            raise typer.Exit(1)

        html = page.content()
        browser.close()
        return html
