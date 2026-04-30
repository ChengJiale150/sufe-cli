import typer

from .summary import summary
from .list_cmd import list_scores

app = typer.Typer(help="SUFE 成绩查询相关命令")

app.command()(summary)
app.command(name="list")(list_scores)
