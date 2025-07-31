import functools
from collections.abc import Callable

import click


def common_params(func: Callable) -> Callable:
    @functools.wraps(func)
    @click.option(
        "--platform", help="Target platform (e.g. linux-aarch64). If not specified, all platforms will be analyzed"
    )
    @click.option("--compressed", is_flag=True, help="Measure compressed size")
    @click.option(
        "--format",
        help="Format of the output (comma-separated values: png, csv, markdown, json)",
        callback=lambda _, __, v: v.split(",") if v else [],
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
