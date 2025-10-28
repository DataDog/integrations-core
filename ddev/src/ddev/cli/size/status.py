# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import click

from ddev.cli.application import Application
from ddev.cli.size.utils.common_params import common_params
from ddev.cli.size.utils.size_model import Sizes
from ddev.utils.fs import Path

if TYPE_CHECKING:
    from ddev.cli.size.utils.common_funcs import CLIParameters


@click.command()
@click.option("--to-dd-org", type=str, help="Send metrics to Datadog using the specified organization name.")
@click.option("--to-dd-key", type=str, help="Send metrics to datadoghq.com using the specified API key.")
@click.option(
    "--to-dd-site",
    type=str,
    help="Send metrics to Datadog using the specified site. If not provided datadoghq.com will be used.",
)
@click.option(
    "--python", "py_version", help="Python version (e.g 3.12).  If not specified, all versions will be analyzed"
)
@click.option("--commit", help="Commit hash to check the dependency sizes status of.")
@common_params  # platform, compressed, format, show_gui
@click.pass_obj
def status(
    app: Application,
    platform: str | None,
    py_version: str | None,
    compressed: bool,
    format: list[str],
    show_gui: bool,
    to_dd_org: str | None,
    to_dd_key: str | None,
    to_dd_site: str | None,
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
            py_version,
            to_dd_org,
            commit,
            to_dd_key,
            to_dd_site,
            app,
        )

        app.display_debug(f"Valid platforms: {valid_platforms}")
        app.display_debug(f"Valid versions: {valid_versions}")

        sizes_plat_ver: Sizes = Sizes([])
        platforms = valid_platforms if platform is None else [platform]
        versions = valid_versions if py_version is None else [py_version]
        combinations = [(p, v) for p in platforms for v in versions]

        commits = None
        dependencies_resolved = False
        dependency_sizes: Sizes = Sizes([])
        previous_sizes = None

        if commit:
            from ddev.cli.size.utils.gha_artifacts import (
                RESOLVE_BUILD_DEPS_WORKFLOW,
                artifact_exists,
                get_status_sizes,
            )

            commits = [commit]
            if not artifact_exists(app, commit, "target-" + next(iter(platforms)), RESOLVE_BUILD_DEPS_WORKFLOW):
                app.display("\n -> Searching for dependency sizes in previous commit")
                previous_sizes, previous_commit = get_status_sizes(app, compressed, branch="master")
                if previous_commit and previous_sizes:
                    app.display_debug(f"Previous commit: {previous_commit}")
            else:
                dependencies_resolved = True

        for plat, ver in combinations:
            if commit and dependencies_resolved:
                from ddev.cli.size.utils.gha_artifacts import get_dep_sizes

                app.display("-> Dependencies were resolved in this commit, using the artifact")
                dependency_sizes = get_dep_sizes(app, commit, plat, ver, compressed)

            elif commit and not dependencies_resolved and previous_sizes:
                dependency_sizes = previous_sizes.filter(platform=plat, python_version=ver, type="Dependency")

            if commit and not dependency_sizes:
                app.display_error("Could not find dependency sizes in the artifacts: falling back to local lockfiles")

            parameters: CLIParameters = {
                "app": app,
                "platform": plat,
                "py_version": ver,
                "compressed": compressed,
                "format": format,
                "show_gui": show_gui,
            }
            status_sizes = status_mode(
                repo_path,
                parameters,
                dependency_sizes,
            )

            sizes_plat_ver = sizes_plat_ver + status_sizes

            if to_dd_org or to_dd_key:
                from ddev.cli.size.utils.common_funcs import SizeMode, send_metrics_to_dd

                app.display("Sending metrics to Datadog ")
                send_metrics_to_dd(
                    app, status_sizes, to_dd_org, to_dd_key, to_dd_site, compressed, SizeMode.STATUS, commits
                )

        if format:
            from ddev.cli.size.utils.common_funcs import SizeMode, export_format

            export_format(app, format, sizes_plat_ver, SizeMode.STATUS, compressed)

    except Exception:
        import traceback

        app.abort(traceback.format_exc())


def status_mode(
    repo_path: Path,
    params: CLIParameters,
    dependency_sizes: Sizes | None,
) -> Sizes:
    from ddev.cli.size.utils.common_funcs import (
        get_dependencies,
        get_files,
    )

    format = params["format"]
    platform = params["platform"]
    py_version = params["py_version"]
    compressed = params["compressed"]
    show_gui = params["show_gui"]
    app = params["app"]

    with app.status("Calculating sizes..."):
        sizes = get_files(repo_path, compressed, py_version, platform) + (
            dependency_sizes or get_dependencies(app, repo_path, platform, py_version, compressed)
        )

    sizes.sort()

    if not format or format == ["png"]:  # if no format is provided for the data print the table
        sizes.print_table(app, f"Disk Usage Status for {platform} and Python version {py_version}")

    treemap_path = None
    if format and "png" in format:
        treemap_path = os.path.join("size_status_visualizations", f"treemap_{platform}_{py_version}.png")

    if show_gui or treemap_path:
        from ddev.cli.size.utils.common_funcs import SizeMode, plot_treemap

        plot_treemap(
            app,
            sizes,
            f"Disk Usage Status for {platform} and Python version {py_version}",
            show_gui,
            SizeMode.STATUS,
            treemap_path,
        )

    return sizes


def validate_parameters(
    valid_platforms: set[str],
    valid_versions: set[str],
    platform: str | None,
    py_version: str | None,
    to_dd_org: str | None,
    commit: str | None,
    to_dd_key: str | None,
    to_dd_site: str | None,
    app: Application,
) -> None:
    errors = []
    if platform and platform not in valid_platforms:
        errors.append(f"Invalid platform: {platform!r}")

    if py_version and py_version not in valid_versions:
        errors.append(f"Invalid version: {py_version!r}")

    if commit and len(commit) != 40:
        errors.append("Dependency commit must be a full length commit hash.")

    if to_dd_site and not to_dd_key:
        errors.append("If --to-dd-site is provided, --to-dd-key must also be provided.")

    if to_dd_site and to_dd_org:
        errors.append("If --to-dd-org is provided, --to-dd-site must not be provided.")

    if to_dd_key and to_dd_org:
        errors.append("If --to-dd-org is provided, --to-dd-key must not be provided.")

    if errors:
        app.abort("\n".join(errors))
