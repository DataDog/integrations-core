import functools
from collections.abc import Callable

import click

VALID_FORMATS = ["png", "csv", "markdown", "json"]


def common_params(func: Callable) -> Callable:
    @functools.wraps(func)
    @click.option(
        "--platform", help="Target platform (e.g. linux-aarch64). If not specified, all platforms will be analyzed"
    )
    @click.option("--compressed", is_flag=True, help="Measure compressed size")
    @click.option(
        "--format",
        help=f"Format of the output (comma-separated values: {', '.join(VALID_FORMATS)})",
        callback=validate_format,
    )
    @click.option(
        "--show-gui",
        is_flag=True,
        help="Display a pop-up window with a treemap showing the current size distribution of modules.",
    )
    @click.pass_context
    def wrapper(
        ctx: click.Context, platform: str, compressed: bool, format: list[str], show_gui: bool, *args, **kwargs
    ):
        kwargs["platform"] = platform
        kwargs["compressed"] = compressed
        kwargs["format"] = format
        kwargs["show_gui"] = show_gui
        return ctx.invoke(func, *args, **kwargs)

    return wrapper


def validate_format(_, __, format: str) -> list[str]:
    format_list = [f.strip() for f in format.split(",")] if format else []

    if unsupported_formats := set(format_list) - set(VALID_FORMATS):
        raise click.BadParameter(
            f"Invalid format: {', '.join(unsupported_formats)}. Only {', '.join(VALID_FORMATS)} are supported."
        )
    return format_list
