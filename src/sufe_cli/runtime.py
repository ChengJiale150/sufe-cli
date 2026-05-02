from dataclasses import dataclass
import sys


@dataclass(frozen=True)
class CliContext:
    timeout: int = 30
    debug: bool = False


_current_context = CliContext()


def set_cli_context(context: CliContext) -> None:
    global _current_context
    _current_context = context


def get_cli_context(context: CliContext | None = None) -> CliContext:
    return _current_context if context is None else context


def debug_log(message: str, context: CliContext | None = None) -> None:
    if get_cli_context(context).debug:
        print(message, file=sys.stderr)
