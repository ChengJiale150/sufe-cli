import typer

from .course import app as course_app
from .assignment import app as assignment_app

app = typer.Typer(help="SUFE Canvas 相关命令")

app.add_typer(course_app, name="course")
app.add_typer(assignment_app, name="assignment")
