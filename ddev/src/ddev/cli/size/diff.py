# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from datetime import datetime
from typing import Optional

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from ddev.cli.application import Application
from ddev.cli.size.utils.common_params import common_params

from .utils.common_funcs import (
    CLIParameters,
    FileDataEntry,
    FileDataEntryPlatformVersion,
    GitRepo,
    convert_to_human_readable_size,
    export_format,
    format_modules,
    get_dependencies,
    get_files,
    get_valid_platforms,
    get_valid_versions,
    plot_treemap,
    print_table,
)

console = Console(stderr=True)
MINIMUM_DATE = datetime.strptime("Sep 17 2024", "%b %d %Y").date()
MINIMUM_LENGTH_COMMIT = 7


@click.command()
@click.argument("first_commit")
@click.argument("second_commit")
@click.option("--python", "version", help="Python version (e.g 3.12).  If not specified, all versions will be analyzed")
@common_params  # platform, compressed, format, show_gui
@click.pass_obj
def diff(
    app: Application,
    first_commit: str,
    second_commit: str,
    platform: Optional[str],
    version: Optional[str],
    compressed: bool,
    format: list[str],
    show_gui: bool,
) -> None:
    """
    Compare the size of integrations and dependencies between two commits.
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        transient=True,
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Calculating differences...", total=None)
        if len(first_commit) < MINIMUM_LENGTH_COMMIT and len(second_commit) < MINIMUM_LENGTH_COMMIT:
            raise click.BadParameter(f"Commit hashes must be at least {MINIMUM_LENGTH_COMMIT} characters long")
        elif len(first_commit) < MINIMUM_LENGTH_COMMIT:
            raise click.BadParameter(
                f"First commit hash must be at least {MINIMUM_LENGTH_COMMIT} characters long.",
                param_hint="first_commit",
            )
        elif len(second_commit) < MINIMUM_LENGTH_COMMIT:
            raise click.BadParameter(
                f"Second commit hash must be at least {MINIMUM_LENGTH_COMMIT} characters long.",
                param_hint="second_commit",
            )
        if first_commit == second_commit:
            raise click.BadParameter("Commit hashes must be different")
        if format:
            for fmt in format:
                if fmt not in ["png", "csv", "markdown", "json"]:
                    raise ValueError(f"Invalid format: {fmt}. Only png, csv, markdown, and json are supported.")
        repo_url = app.repo.path

        with GitRepo(repo_url) as gitRepo:
            try:
                date_str, _, _ = gitRepo.get_commit_metadata(first_commit)
                date = datetime.strptime(date_str, "%b %d %Y").date()
                if date < MINIMUM_DATE:
                    raise ValueError(f"First commit must be after {MINIMUM_DATE.strftime('%b %d %Y')} ")
                valid_versions = get_valid_versions(gitRepo.repo_dir)
                valid_platforms = get_valid_platforms(gitRepo.repo_dir, valid_versions)
                if platform and platform not in valid_platforms:
                    raise ValueError(f"Invalid platform: {platform}")
                elif version and version not in valid_versions:
                    raise ValueError(f"Invalid version: {version}")
                modules_plat_ver: list[FileDataEntryPlatformVersion] = []
                platforms = valid_platforms if platform is None else [platform]
                versions = valid_versions if version is None else [version]
                progress.remove_task(task)
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
                        diff_mode(
                            gitRepo,
                            first_commit,
                            second_commit,
                            parameters,
                            progress,
                        )
                    )
                if format:
                    export_format(app, format, modules_plat_ver, "diff", platform, version, compressed)
            except Exception as e:
                progress.stop()
                app.abort(str(e))
        return None


def diff_mode(
    gitRepo: GitRepo,
    first_commit: str,
    second_commit: str,
    params: CLIParameters,
    progress: Progress,
) -> list[FileDataEntryPlatformVersion]:
    files_b, dependencies_b, files_a, dependencies_a = get_repo_info(
        gitRepo, params["platform"], params["version"], first_commit, second_commit, params["compressed"], progress
    )

    integrations = get_diff(files_b, files_a, "Integration")
    dependencies = get_diff(dependencies_b, dependencies_a, "Dependency")

    if integrations + dependencies == []:
        params["app"].display(
            f"No size differences were detected between the selected commits for {params['platform']}"
        )
        return []
    else:
        formatted_modules = format_modules(integrations + dependencies, params["platform"], params["version"])
        formatted_modules.sort(key=lambda x: x["Size_Bytes"], reverse=True)
        for module in formatted_modules:
            if module["Size_Bytes"] > 0:
                module["Size"] = f"+{module['Size']}"

    if not params["format"] or params["format"] == ["png"]:  # if no format is provided for the data print the table
        print_table(params["app"], "Diff", formatted_modules)

    treemap_path = None
    if params["format"] and "png" in params["format"]:
        treemap_path = os.path.join("size_diff_visualizations", f"treemap_{params['platform']}_{params['version']}.png")

    if params["show_gui"] or treemap_path:
        plot_treemap(
            params["app"],
            formatted_modules,
            f"Disk Usage Differences for {params['platform']} and Python version {params['version']}",
            params["show_gui"],
            "diff",
            treemap_path,
        )

    return formatted_modules


def get_repo_info(
    gitRepo: GitRepo,
    platform: str,
    version: str,
    first_commit: str,
    second_commit: str,
    compressed: bool,
    progress: Progress,
) -> tuple[list[FileDataEntry], list[FileDataEntry], list[FileDataEntry], list[FileDataEntry]]:
    with progress:
        """
        Retrieves integration and dependency sizes for two commits in the repo.

        Args:
            gitRepo: An instance of GitRepo for accessing the repository.
            platform: Target platform for dependency resolution.
            version: Python version for dependency resolution.
            first_commit: The earlier commit SHA to compare.
            second_commit: The later commit SHA to compare.
            compressed: Whether to measure compressed sizes.
            progress: Rich Progress bar.

        Returns:
            A tuple of four lists:
                - files_b: Integration sizes at first_commit
                - dependencies_b: Dependency sizes at first_commit
                - files_a: Integration sizes at second_commit
                - dependencies_a: Dependency sizes at second_commit
        """

        repo = gitRepo.repo_dir
        task = progress.add_task("[cyan]Calculating sizes for the first commit...", total=None)
        gitRepo.checkout_commit(first_commit)
        files_b = get_files(repo, compressed, version)
        dependencies_b = get_dependencies(repo, platform, version, compressed)
        progress.remove_task(task)

        task = progress.add_task("[cyan]Calculating sizes for the second commit...", total=None)
        gitRepo.checkout_commit(second_commit)
        files_a = get_files(repo, compressed, version)
        dependencies_a = get_dependencies(repo, platform, version, compressed)
        progress.remove_task(task)

    return files_b, dependencies_b, files_a, dependencies_a


def get_diff(
    size_first_commit: list[FileDataEntry], size_second_commit: list[FileDataEntry], type: str
) -> list[FileDataEntry]:
    """
    Computes size differences between two sets of integrations or dependencies.

    Args:
        size_first_commit: Entries from the first (earlier) commit.
        size_second_commit: Entries from the second (later) commit.
        type: Integration/Dependency

    Returns:
        A list of FileDataEntry items representing only the entries with a size difference.
        Entries include new, deleted, or changed modules, with delta size in bytes and human-readable format.
    """

    first_commit = {entry["Name"]: entry for entry in size_first_commit}
    second_commit = {entry["Name"]: entry for entry in size_second_commit}

    all_names = set(first_commit) | set(second_commit)
    diffs: list[FileDataEntry] = []

    for name in all_names:
        b = first_commit.get(name)
        a = second_commit.get(name)

        size_b = b["Size_Bytes"] if b else 0
        size_a = a["Size_Bytes"] if a else 0
        delta = size_a - size_b

        if delta == 0:
            continue

        ver_b = b["Version"] if b else ""
        ver_a = a["Version"] if a else ""

        if size_b == 0:
            name_str = f"{name} (NEW)"
            version_str = ver_a
        elif size_a == 0:
            name_str = f"{name} (DELETED)"
            version_str = ver_b
        else:
            name_str = name
            version_str = f"{ver_b} -> {ver_a}" if ver_a != ver_b else ver_a

        diffs.append(
            {
                "Name": name_str,
                "Version": version_str,
                "Type": type,
                "Size_Bytes": delta,
                "Size": convert_to_human_readable_size(delta),
            }
        )

    return diffs
