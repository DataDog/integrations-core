# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os  # noqa: I001
from pathlib import Path
from typing import List, Optional, Literal, overload

import click
from rich.console import Console

from ddev.cli.application import Application

from .common import (
    FileDataEntry,
    FileDataEntryPlatformVersion,
    Parameters,
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

console = Console(stderr=True)


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
            modules_plat_ver: List[FileDataEntryPlatformVersion] = []
            platforms = valid_platforms if platform is None else [platform]
            versions = valid_versions if version is None else [version]
            combinations = [(p, v) for p in platforms for v in versions]
            for plat, ver in combinations:
                multiple_plats_and_vers: Literal[True] = True
                path = None
                if save_to_png_path:
                    base, ext = os.path.splitext(save_to_png_path)
                    path = f"{base}_{plat}_{ver}{ext}"
                parameters: Parameters = {
                    "app": app,
                    "platform": plat,
                    "version": ver,
                    "compressed": compressed,
                    "csv": csv,
                    "markdown": markdown,
                    "json": json,
                    "save_to_png_path": path,
                    "show_gui": show_gui,
                }
                modules_plat_ver.extend(
                    status_mode(
                        repo_path,
                        parameters,
                        multiple_plats_and_vers,
                    )
                )
            if csv:
                print_csv(app, modules_plat_ver)
            elif json:
                print_json(app, modules_plat_ver)
        else:
            modules: List[FileDataEntry] = []
            multiple_plat_and_ver: Literal[False] = False
            base_parameters: Parameters = {
                "app": app,
                "platform": platform,
                "version": version,
                "compressed": compressed,
                "csv": csv,
                "markdown": markdown,
                "json": json,
                "save_to_png_path": save_to_png_path,
                "show_gui": show_gui,
            }
            modules.extend(
                status_mode(
                    repo_path,
                    base_parameters,
                    multiple_plat_and_ver,
                )
            )
            if csv:
                print_csv(app, modules)
            elif json:
                print_json(app, modules)

    except Exception as e:
        app.abort(str(e))


@overload
def status_mode(
    repo_path: Path,
    params: Parameters,
    multiple_plats_and_vers: Literal[True],
) -> List[FileDataEntryPlatformVersion]: ...
@overload
def status_mode(
    repo_path: Path,
    params: Parameters,
    multiple_plats_and_vers: Literal[False],
) -> List[FileDataEntry]: ...
def status_mode(
    repo_path: Path,
    params: Parameters,
    multiple_plats_and_vers: bool,
) -> List[FileDataEntryPlatformVersion] | List[FileDataEntry]:
    with console.status("[cyan]Calculating sizes...", spinner="dots"):
        modules = get_files(repo_path, params["compressed"]) + get_dependencies(
            repo_path, params["platform"], params["version"], params["compressed"]
        )

    formatted_modules = format_modules(modules, params["platform"], params["version"], multiple_plats_and_vers)
    formatted_modules.sort(key=lambda x: x["Size_Bytes"], reverse=True)

    if params["markdown"]:
        print_markdown(params["app"], "Status", formatted_modules)
    elif not params["csv"] and not params["json"]:
        print_table(params["app"], "Status", formatted_modules)

    if params["show_gui"] or params["save_to_png_path"]:
        plot_treemap(
            formatted_modules,
            f"Disk Usage Status for {params['platform']} and Python version {params['version']}",
            params["show_gui"],
            "status",
            params["save_to_png_path"],
        )

    return formatted_modules
