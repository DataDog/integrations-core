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
    CLIParameters,
    FileDataEntryPlatformVersion,
    format_modules,
    get_dependencies,
    get_files,
    get_valid_platforms,
    get_valid_versions,
    plot_treemap,
    print_table,
    save_csv,
    save_json,
    save_markdown,
    send_metrics_to_dd,
)

console = Console(stderr=True)


@click.command()
@click.option(
    "--platform", help="Target platform (e.g. linux-aarch64). If not specified, all platforms will be analyzed"
)
@click.option("--python", "version", help="Python version (e.g 3.12).  If not specified, all versions will be analyzed")
@click.option("--compressed", is_flag=True, help="Measure compressed size")
@click.option("--format", type=click.Choice(["png", "csv", "markdown", "json"]), help="Format of the output", multiple=True)
@click.option(
    "--show-gui",
    is_flag=True,
    help="Display a pop-up window with a treemap showing the current size distribution of modules.",
)
@click.option("--send-metrics-dd-org", type=str, help="Send metrics to Datadog using the specified organization name.")
@click.pass_obj
def status(
    app: Application,
    platform: Optional[str],
    version: Optional[str],
    compressed: bool,
    format: list[str],
    show_gui: bool,
    send_metrics_dd_org: str,
) -> None:
    """
    Show the current size of all integrations and dependencies.
    """
    try:
        repo_path = app.repo.path
        valid_platforms = get_valid_platforms(repo_path)
        valid_versions = get_valid_versions(repo_path)
        if platform and platform not in valid_platforms:
            raise ValueError(f"Invalid platform: {platform}")
        elif version and version not in valid_versions:
            raise ValueError(f"Invalid version: {version}")

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

        size_type = "compressed" if compressed else "uncompressed"
        for output_format in format:
            if output_format == "csv":
                csv_filename = (
                    f"{platform}_{version}_{size_type}_status.csv" if platform and version else
                    f"{version}_{size_type}_status.csv" if version else
                    f"{platform}_{size_type}_status.csv" if platform else
                    f"{size_type}_status.csv"
                )
                save_csv(app, modules_plat_ver, csv_filename)

            elif output_format == "json":
                json_filename = (
                    f"{platform}_{version}_{size_type}_status.json" if platform and version else
                    f"{version}_{size_type}_status.json" if version else
                    f"{platform}_{size_type}_status.json" if platform else
                    f"{size_type}_status.json"
                )
                save_json(json_filename, modules_plat_ver)

            elif output_format == "markdown":
                markdown_filename = (
                    f"{platform}_{version}_{size_type}_status.md" if platform and version else
                    f"{version}_{size_type}_status.md" if version else
                    f"{platform}_{size_type}_status.md" if platform else
                    f"{size_type}_status.md"
                )
                with open(markdown_filename, 'w', encoding='utf-8'):
                    pass
            if send_metrics_dd_org:
                send_metrics_to_dd(app, modules_plat_ver, send_metrics_dd_org, compressed)
    except Exception as e:
        app.abort(str(e))


def status_mode(
    repo_path: Path,
    params: CLIParameters,
) -> list[FileDataEntryPlatformVersion]:
    with console.status("[cyan]Calculating sizes...", spinner="dots"):
        modules = get_files(repo_path, params["compressed"]) + get_dependencies(
            repo_path, params["platform"], params["version"], params["compressed"]
        )

    formatted_modules = format_modules(modules, params["platform"], params["version"])
    formatted_modules.sort(key=lambda x: x["Size_Bytes"], reverse=True)

    if params["markdown"]:
        save_markdown(params["app"], "Status", formatted_modules)
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
