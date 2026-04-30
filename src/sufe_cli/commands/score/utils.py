import typer
from bs4 import BeautifulSoup


def print_tsv(headers: list[str], rows: list[list[str]]) -> None:
    """以 TSV 格式打印表头和数据行。"""
    typer.echo("\t".join(headers))
    for row in rows:
        typer.echo("\t".join(row))


def parse_summary(html: str) -> tuple[list[str], list[list[str]]]:
    """解析学期汇总表格，返回 (表头, 数据行)。"""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="gridtable")
    if not table:
        return [], []

    tbody = table.find("tbody")
    if not tbody:
        return [], []

    headers = ["学年度", "学期", "门数", "平均成绩", "总学分", "平均绩点"]
    rows: list[list[str]] = []

    for tr in tbody.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 6:
            continue

        # 跳过统计时间行（含 th）
        if tr.find("th"):
            continue

        # 提取每列文本，门数列可能含 hidden input，取可见文本
        cols = [td.get_text(strip=True) for td in tds[:6]]

        if cols:
            rows.append(cols)

    return headers, rows


def parse_courses(html: str) -> tuple[list[str], list[list[str]]]:
    """解析详细成绩表格，返回 (表头, 数据行)。"""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="grid21344342991")
    if not table:
        return [], []

    tbody = table.find("tbody", id="grid21344342991_data")
    if not tbody:
        return [], []

    headers = [
        "学年学期",
        "课程代码",
        "课程序号",
        "课程名称",
        "课程类别",
        "学分",
        "总评成绩",
        "最终",
        "绩点",
    ]
    rows: list[list[str]] = []

    for tr in tbody.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 9:
            continue

        cols = [td.get_text(strip=True) for td in tds[:9]]
        if cols:
            rows.append(cols)

    return headers, rows
