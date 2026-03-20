# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import click

from ddev.cli.application import Application
from ddev.cli.size.utils.common_params import common_params

if TYPE_CHECKING:
    from ddev.cli.size.utils.common_funcs import (
        CLIParameters,
        FileDataEntryPlatformVersion,
    )
    from ddev.utils.fs import Path


@click.command()
@click.option("--to-dd-org", type=str, help="Send metrics to Datadog using the specified organization name.")
@click.option("--to-dd-key", type=str, help="Send metrics to datadoghq.com using the specified API key.")
@click.option("--branch", help="Branch name to tag metrics with. Required when sending metrics to Datadog.")
@click.option("--python", "version", help="Python version (e.g 3.12).  If not specified, all versions will be analyzed")
@click.option(
    "--commit",
    help=(
        "Commit hash to associate metrics with. Required when sending metrics to Datadog. "
        "For declared sizes, it also identifies which artifact to fetch dependency sizes from. "
    ),
)
@click.option(
    "--declared",
    is_flag=True,
    default=False,
    help="Measure declared sizes by fetching dependency sizes from the commit's artifact. Requires --commit.",
)
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
    branch: str | None,
    commit: str | None,
    declared: bool,
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
            to_dd_key,
            branch,
            declared,
            app,
        )

        modules_plat_ver: list[FileDataEntryPlatformVersion] = []
        platforms = valid_platforms if platform is None else [platform]
        versions = valid_versions if version is None else [version]
        combinations = [(p, v) for p in platforms for v in versions]

        for plat, ver in combinations:
            dependency_sizes = None
            if declared:
                from ddev.cli.size.utils.common_funcs import get_last_dependency_sizes_artifact

                dependency_sizes = get_last_dependency_sizes_artifact(app, commit, plat, ver, compressed)
                if not dependency_sizes:
                    app.abort("Could not find dependency sizes in the artifacts. Declared sizes are not available.")

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
        if (to_dd_org or to_dd_key) and commit and branch:
            from ddev.cli.size.utils.common_funcs import send_metrics_to_dd

            size_source = "declared" if declared else "locked"
            send_metrics_to_dd(app, commit, modules_plat_ver, to_dd_org, to_dd_key, compressed, branch, size_source)
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
    to_dd_key: str | None,
    branch: str | None,
    declared: bool,
    app: Application,
) -> None:
    errors = []
    if platform and platform not in valid_platforms:
        errors.append(f"Invalid platform: {platform!r}")

    if version and version not in valid_versions:
        errors.append(f"Invalid version: {version!r}")

    if declared and not commit:
        errors.append("--declared requires --commit to identify which artifact to fetch dependency sizes from.")

    if format:
        for fmt in format:
            if fmt not in ["png", "csv", "markdown", "json"]:
                errors.append(f"Invalid format: {fmt!r}. Only png, csv, markdown, and json are supported.")

    if to_dd_org and to_dd_key:
        errors.append("Specify either --to-dd-org or --to-dd-key, not both")

    if (to_dd_org or to_dd_key) and not commit:
        errors.append("--commit is required when sending metrics to Datadog.")

    if (to_dd_org or to_dd_key) and not branch:
        errors.append("--branch is required when sending metrics to Datadog.")

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
