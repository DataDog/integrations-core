# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import click

from ddev.cli.application import Application
from ddev.cli.size.utils.common_params import common_params
from ddev.utils.fs import Path

if TYPE_CHECKING:
    from ddev.cli.size.utils.common_funcs import (
        CLIParameters,
        FileDataEntryPlatformVersion,
    )


@click.command()
@click.option("--to-dd-org", type=str, help="Send metrics to Datadog using the specified organization name.")
@click.option("--to-dd-key", type=str, help="Send metrics to datadoghq.com using the specified API key.")
@click.option("--python", "version", help="Python version (e.g 3.12).  If not specified, all versions will be analyzed")
@click.option("--dependency-sizes", type=click.Path(exists=True), help="Path to the dependency sizes file. If no")
@click.option("--commit", help="Commit hash to check the status of. It takes the commit's dependency sizes file.")
@common_params  # platform, compressed, format, show_gui
@click.pass_obj
def status(
    app: Application,
    platform: str | None,
    version: str | None,
    compressed: bool,
    format: list[str],
    show_gui: bool,
    to_dd_org: str | None,
    to_dd_key: str | None,
    dependency_sizes: Path | None,
    commit: str | None,
) -> None:
    """
    Show the current size of all integrations and dependencies in your local repo.
    By default, it analyzes every platform and Python version using your local lockfiles
    and prints the results to the terminal.

    """
    from ddev.cli.size.utils.common_funcs import (
        get_valid_platforms,
        get_valid_versions,
    )

    try:
        repo_path = app.repo.path
        valid_versions = get_valid_versions(repo_path)
        valid_platforms = get_valid_platforms(repo_path, valid_versions)

        validate_parameters(
            valid_platforms,
            valid_versions,
            platform,
            version,
            format,
            to_dd_org,
            commit,
            dependency_sizes,
            to_dd_key,
            app,
        )

        modules_plat_ver: list[FileDataEntryPlatformVersion] = []
        platforms = valid_platforms if platform is None else [platform]
        versions = valid_versions if version is None else [version]
        combinations = [(p, v) for p in platforms for v in versions]

        for plat, ver in combinations:
            if commit:
                from ddev.cli.size.utils.common_funcs import get_last_dependency_sizes_artifact

                dependency_sizes = get_last_dependency_sizes_artifact(app, commit, plat, ver, compressed)
                if not dependency_sizes:
                    app.display_error(
                        "Could not find dependency sizes in the artifacts: falling back to local lockfiles"
                    )

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
                    dependency_sizes,
                )
            )
        if format:
            from ddev.cli.size.utils.common_funcs import export_format

            export_format(app, format, modules_plat_ver, "status", platform, version, compressed)
        if to_dd_org or to_dd_key:
            from ddev.cli.size.utils.common_funcs import send_metrics_to_dd

            send_metrics_to_dd(app, commit, modules_plat_ver, to_dd_org, to_dd_key, compressed)
    except Exception as e:
        app.abort(str(e))


def validate_parameters(
    valid_platforms: set[str],
    valid_versions: set[str],
    platform: str | None,
    version: str | None,
    format: list[str],
    to_dd_org: str | None,
    commit: str | None,
    dependency_sizes: Path | None,
    to_dd_key: str | None,
    app: Application,
) -> None:
    errors = []
    if platform and platform not in valid_platforms:
        errors.append(f"Invalid platform: {platform!r}")

    if version and version not in valid_versions:
        errors.append(f"Invalid version: {version!r}")

    if commit and dependency_sizes:
        errors.append("Pass either 'commit' or 'dependency-sizes'. Both options cannot be supplied.")

    if format:
        for fmt in format:
            if fmt not in ["png", "csv", "markdown", "json"]:
                errors.append(f"Invalid format: {fmt!r}. Only png, csv, markdown, and json are supported.")

    if dependency_sizes and not dependency_sizes.is_file():
        errors.append(f"Dependency sizes file does not exist: {dependency_sizes!r}")

    if to_dd_org and to_dd_key:
        errors.append("Specify either --to-dd-org or --to-dd-key, not both")

    if (to_dd_org or to_dd_key) and not commit:
        errors.append("In order to send metrics to Datadog, you need to provide a commit hash")

    if errors:
        app.abort("\n".join(errors))


def status_mode(
    repo_path: Path,
    params: CLIParameters,
    dependency_sizes: Path | None,
) -> list[FileDataEntryPlatformVersion]:
    from ddev.cli.size.utils.common_funcs import (
        format_modules,
        get_dependencies,
        get_files,
        print_table,
    )

    with params["app"].status("Calculating sizes..."):
        if dependency_sizes:
            from ddev.cli.size.utils.common_funcs import get_dependencies_from_json

            params["app"].display_debug(
                f"Getting dependencies from artifacts for {params['platform']} {params['version']}"
            )
            modules = get_files(repo_path, params["compressed"], params["version"]) + get_dependencies_from_json(
                dependency_sizes, params["platform"], params["version"], params["compressed"]
            )

        else:
            params["app"].display_debug(
                f"Getting dependencies from lockfiles for {params['platform']} {params['version']}"
            )
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
        from ddev.cli.size.utils.common_funcs import plot_treemap

        plot_treemap(
            params["app"],
            formatted_modules,
            f"Disk Usage Status for {params['platform']} and Python version {params['version']}",
            params["show_gui"],
            "status",
            treemap_path,
        )

    return formatted_modules
