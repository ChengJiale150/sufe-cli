import typer

from .fetcher import fetch_grade_page
from .utils import parse_summary, print_tsv


def summary() -> None:
    """获取学期总成绩汇总（TSV 格式）。"""
    html = fetch_grade_page()
    headers, rows = parse_summary(html)
    if not rows:
        typer.secho("未解析到汇总数据，请检查页面内容。", fg=typer.colors.YELLOW)
        raise typer.Exit(1)
    print_tsv(headers, rows)
