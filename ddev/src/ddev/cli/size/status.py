# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from ddev.cli.application import Application

from .common import (
    format_modules,
    get_dependencies,
    get_files,
    get_valid_platforms,
    get_valid_versions,
    plot_treemap,
    print_csv,
    print_json,
    print_markdown,
    print_table,
)

console = Console()


@click.command()
@click.option(
    "--platform", help="Target platform (e.g. linux-aarch64). If not specified, all platforms will be analyzed"
)
@click.option("--python", "version", help="Python version (e.g 3.12).  If not specified, all versions will be analyzed")
@click.option("--compressed", is_flag=True, help="Measure compressed size")
@click.option("--csv", is_flag=True, help="Output in CSV format")
@click.option("--markdown", is_flag=True, help="Output in Markdown format")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.option("--save_to_png_path", help="Path to save the treemap as PNG")
@click.option(
    "--show_gui",
    is_flag=True,
    help="Display a pop-up window with a treemap showing the current size distribution of modules.",
)
@click.pass_obj
def status(
    app: Application,
    platform: Optional[str],
    version: Optional[str],
    compressed: bool,
    csv: bool,
    markdown: bool,
    json: bool,
    save_to_png_path: Optional[str],
    show_gui: bool,
) -> None:
    """
    Show the current size of all integrations and dependencies.
    """
    try:
        if sum([csv, markdown, json]) > 1:
            raise click.BadParameter("Only one output format can be selected: --csv, --markdown, or --json")
        repo_path = app.repo.path
        valid_platforms = get_valid_platforms(repo_path)
        valid_versions = get_valid_versions(repo_path)
        if platform and platform not in valid_platforms:
            raise ValueError(f"Invalid platform: {platform}")
        elif version and version not in valid_versions:
            raise ValueError(f"Invalid version: {version}")
        if platform is None or version is None:
            platforms = valid_platforms if platform is None else [platform]
            versions = valid_versions if version is None else [version]
            combinations = [(p, v) for p in platforms for v in versions]
            for i, (plat, ver) in enumerate(combinations):
                path = None
                if save_to_png_path:
                    base, ext = os.path.splitext(save_to_png_path)
                    path = f"{base}_{plat}_{ver}{ext}"
                status_mode(
                    app, repo_path, plat, ver, compressed, csv, markdown, json, i, path, show_gui, len(combinations)
                )

        else:
            status_mode(
                app,
                repo_path,
                platform,
                version,
                compressed,
                csv,
                markdown,
                json,
                None,
                save_to_png_path,
                show_gui,
                None,
            )

    except Exception as e:
        app.abort(str(e))


def status_mode(
    app: Application,
    repo_path: Path,
    platform: str,
    version: str,
    compressed: bool,
    csv: bool,
    markdown: bool,
    json: bool,
    i: Optional[int],
    save_to_png_path: Optional[str],
    show_gui: bool,
    n_iterations: Optional[int],
) -> None:
    with console.status("[cyan]Calculating sizes...", spinner="dots"):
        modules = get_files(repo_path, compressed) + get_dependencies(repo_path, platform, version, compressed)
    formated_modules = format_modules(modules, platform, version, i)
    formated_modules.sort(key=lambda x: x["Size_Bytes"], reverse=True)

    if csv:
        print_csv(app, i, formated_modules)
    elif json:
        print_json(app, i, n_iterations, False, formated_modules)
    elif markdown:
        print_markdown(app, "Status", formated_modules)
    else:
        print_table(app, "Status", formated_modules)

    if show_gui or save_to_png_path:
        plot_treemap(
            formated_modules,
            f"Disk Usage Status for {platform} and Python version {version}",
            show_gui,
            "status",
            save_to_png_path,
        )
