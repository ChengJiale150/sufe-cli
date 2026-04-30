import typer
from .lclibrary import app as lclibrary_app


app = typer.Typer(help="SUFE 核心命令")
app.add_typer(lclibrary_app, name="lclibrary")