import typer

from .fetcher import fetch_grade_page
from .utils import parse_courses, print_tsv


def list_scores(
    semester: str = typer.Option(None, "--semester", "-s", help="筛选特定学期，如 '2025-2026 1'"),
) -> None:
    """获取全部学科成绩（TSV 格式），可指定学期筛选。"""
    html = fetch_grade_page()
    headers, rows = parse_courses(html)
    if not rows:
        typer.secho("未解析到成绩数据，请检查页面内容。", fg=typer.colors.YELLOW)
        raise typer.Exit(1)

    if semester:
        rows = [r for r in rows if r[0] == semester]
        if not rows:
            typer.secho(f"未找到学期 '{semester}' 的成绩数据。", fg=typer.colors.YELLOW)
            raise typer.Exit(1)

    print_tsv(headers, rows)
