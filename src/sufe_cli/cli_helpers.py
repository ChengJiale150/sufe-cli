from collections.abc import Callable
from functools import wraps
from typing import NoReturn, ParamSpec, TypeVar

import typer

from .errors import SufeCliError

P = ParamSpec("P")
R = TypeVar("R")


def handle_cli_error(error: SufeCliError) -> NoReturn:
    typer.secho(str(error), fg=typer.colors.RED, err=True)
    raise typer.Exit(error.exit_code)


def cli_error_boundary(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except SufeCliError as error:
            handle_cli_error(error)

    return wrapper
