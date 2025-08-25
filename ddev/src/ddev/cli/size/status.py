# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from ddev.cli.application import Application
from ddev.cli.size.utils.common_funcs import (
    CLIParameters,
    FileDataEntryPlatformVersion,
    export_format,
    format_modules,
    get_dependencies,
    get_files,
    get_valid_platforms,
    get_valid_versions,
    plot_treemap,
    print_table,
    send_metrics_to_dd,
)
from ddev.cli.size.utils.common_params import common_params

console = Console(stderr=True)


@click.command()
@click.option("--to-dd-org", type=str, help="Send metrics to Datadog using the specified organization name.")
@click.option("--to-dd-key", type=str, help="Send metrics to datadoghq.com using the specified API key.")
@click.option("--python", "version", help="Python version (e.g 3.12).  If not specified, all versions will be analyzed")
@common_params  # platform, compressed, format, show_gui
@click.pass_obj
def status(
    app: Application,
    platform: Optional[str],
    version: Optional[str],
    compressed: bool,
    format: list[str],
    show_gui: bool,
    to_dd_org: str,
    to_dd_key: str,
) -> None:
    """
    Show the current size of all integrations and dependencies.
    """
    try:
        repo_path = app.repo.path
        valid_versions = get_valid_versions(repo_path)
        valid_platforms = get_valid_platforms(repo_path, valid_versions)
        if platform and platform not in valid_platforms:
            raise ValueError(f"Invalid platform: {platform}")
        elif version and version not in valid_versions:
            raise ValueError(f"Invalid version: {version}")
        elif format:
            for fmt in format:
                if fmt not in ["png", "csv", "markdown", "json"]:
                    raise ValueError(f"Invalid format: {fmt}. Only png, csv, markdown, and json are supported.")
        elif to_dd_org and to_dd_key:
            raise ValueError("Specify either --to-dd-org or --to-dd-key, not both")
        modules_plat_ver: list[FileDataEntryPlatformVersion] = []
        platforms = valid_platforms if platform is None else [platform]
        versions = valid_versions if version is None else [version]
        combinations = [(p, v) for p in platforms for v in versions]
        for plat, ver in combinations:
            parameters: CLIParameters = {
                "app": app,
                "platform": plat,
                "version": ver,
                "compressed": compressed,
                "format": format,
                "show_gui": show_gui,
            }
            modules_plat_ver.extend(
                status_mode(
                    repo_path,
                    parameters,
                )
            )

        if format:
            export_format(app, format, modules_plat_ver, "status", platform, version, compressed)
        if to_dd_org or to_dd_key:
            send_metrics_to_dd(app, modules_plat_ver, to_dd_org, to_dd_key, compressed)
    except Exception as e:
        app.abort(str(e))


def status_mode(
    repo_path: Path,
    params: CLIParameters,
) -> list[FileDataEntryPlatformVersion]:
    with console.status("[cyan]Calculating sizes...", spinner="dots"):
        modules = get_files(repo_path, params["compressed"], params["version"]) + get_dependencies(
            repo_path, params["platform"], params["version"], params["compressed"]
        )

    formatted_modules = format_modules(modules, params["platform"], params["version"])
    formatted_modules.sort(key=lambda x: x["Size_Bytes"], reverse=True)

    if not params["format"] or params["format"] == ["png"]:  # if no format is provided for the data print the table
        print_table(params["app"], "Status", formatted_modules)

    treemap_path = None
    if params["format"] and "png" in params["format"]:
        treemap_path = os.path.join(
            "size_status_visualizations", f"treemap_{params['platform']}_{params['version']}.png"
        )

    if params["show_gui"] or treemap_path:
        plot_treemap(
            params["app"],
            formatted_modules,
            f"Disk Usage Status for {params['platform']} and Python version {params['version']}",
            params["show_gui"],
            "status",
            treemap_path,
        )

    return formatted_modules
