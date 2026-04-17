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
        show_default=True,
        help="Format of the output (comma-separated values: png, csv, markdown, json)",
        callback=lambda _, __, v: v.split(",") if v else [],
    )
    @click.option(
        "--show-gui",
        is_flag=True,
        help="Display a pop-up window with a treemap showing the current size distribution of modules.",
    )
    @click.option(
        "--wheels-storage",
        type=click.Choice(["dev", "stable"]),
        default=None,
        envvar="INTEGRATIONS_WHEELS_STORAGE",
        help=(
            "Which wheel storage tier to resolve dependency URLs against. "
            "Only required for new-style lockfiles that template the storage tier into the URL "
            "via ${INTEGRATIONS_WHEELS_STORAGE}. Old-style lockfiles hard-code the domain and "
            "ignore this option. Can also be set via the INTEGRATIONS_WHEELS_STORAGE env var."
        ),
    )
    @click.pass_context
    def wrapper(
        ctx: click.Context,
        platform: str,
        compressed: bool,
        format: list[str],
        show_gui: bool,
        wheels_storage: str | None,
        *args,
        **kwargs,
    ):
        kwargs["platform"] = platform
        kwargs["compressed"] = compressed
        kwargs["format"] = format
        kwargs["show_gui"] = show_gui
        kwargs["wheels_storage"] = wheels_storage
        return ctx.invoke(func, *args, **kwargs)

    return wrapper
