# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING, Literal

import click

from ddev.cli.application import Application
from ddev.cli.size.utils.common_funcs import GitRepo
from ddev.cli.size.utils.common_params import common_params

if TYPE_CHECKING:
    from ddev.cli.size.utils.common_funcs import CLIParameters, FileDataEntry

MINIMUM_DATE = datetime.strptime("Sep 17 2024", "%b %d %Y").date()
MINIMUM_LENGTH_COMMIT = 7
FULL_LENGTH_COMMIT = 40


@click.command()
@click.argument("new_commit")
@click.option(
    "--compare-to",
    "old_commit",
    help="Commit to compare to. If not specified, will compare to the previous commit on master",
)
@click.option(
    "--python", "py_version", help="Python version (e.g 3.12).  If not specified, all versions will be analyzed"
)
@click.option("--use-artifacts", is_flag=True, help="Fetch sizes from gha artifacts instead of the repo")
@click.option(
    "--quality-gate-threshold",
    type=int,
    help="Percentage threshold for the size difference. Generates the html only if the size"
    " difference is greater than the quality gate threshold",
)
@click.option("--to-dd-org", type=str, help="Send metrics to Datadog using the specified organization name.")
@click.option("--to-dd-key", type=str, help="Send metrics to Datadog using the specified API key.")
@click.option(
    "--to-dd-site",
    type=str,
    help="Send metrics to Datadog using the specified site. If not provided datadoghq.com will be used.",
)
@common_params  # platform, compressed, format, show_gui
@click.pass_obj
def diff(
    app: Application,
    new_commit: str,
    old_commit: str | None,
    platform: str | None,
    py_version: str | None,
    compressed: bool,
    format: list[str],
    show_gui: bool,
    use_artifacts: bool,
    quality_gate_threshold: int | None,
    to_dd_org: str | None,
    to_dd_key: str | None,
    to_dd_site: str | None,
) -> None:
    """
    Compares the size of integrations and dependencies between two commits.

        - If only one commit is given on a feature branch, it's compared to the branch's merge base with master.

        - If only one commit is given while on master, it's compared to the previous commit on master.
    """

    from .utils.common_funcs import (
        get_valid_platforms,
        get_valid_versions,
    )

    with app.status("Calculating differences..."):
        repo_url = app.repo.path
        modules: list[FileDataEntry] = []
        passes_quality_gate = True

        valid_versions = get_valid_versions(app.repo.path)
        valid_platforms = get_valid_platforms(app.repo.path, valid_versions)
        validate_parameters(
            app,
            old_commit,
            new_commit,
            format,
            valid_platforms,
            valid_versions,
            platform,
            py_version,
            to_dd_org,
            to_dd_key,
            to_dd_site,
            use_artifacts,
        )

        platforms = valid_platforms if platform is None else [platform]
        versions = valid_versions if py_version is None else [py_version]
        combinations = [(p, v) for p in platforms for v in versions]
        total_diff = {}
        old_size = {}

        mode: Literal["diff"] = "diff"

        if not old_commit:
            base_commit = app.repo.git.merge_base(new_commit, "origin/master")
            if base_commit != new_commit:
                old_commit = base_commit
            else:
                old_commit = app.repo.git.log(["hash:%H"], n=2, source=new_commit)[1]["hash"]

            app.display(f"Comparing to commit: {old_commit}")
        if use_artifacts:
            from .utils.common_funcs import get_status_sizes_from_commit

            for plat, ver in combinations:
                parameters_artifacts: CLIParameters = {
                    "app": app,
                    "platform": plat,
                    "py_version": ver,
                    "compressed": compressed,
                    "format": format,
                    "show_gui": show_gui,
                }

                try:
                    old_commit_sizes = get_status_sizes_from_commit(
                        app, old_commit, plat, ver, compressed, file=False, only_dependencies=False
                    )
                    new_commit_sizes = get_status_sizes_from_commit(
                        app, new_commit, plat, ver, compressed, file=False, only_dependencies=False
                    )
                except Exception as e:
                    app.abort(str(e))

                if old_commit_sizes is None:
                    app.abort(f"Failed to get sizes for {old_commit=}")
                if new_commit_sizes is None:
                    app.abort(f"Failed to get sizes for {new_commit=}")

                diff_modules, total_diff[(plat, ver)], old_size[(plat, ver)] = calculate_diff(
                    old_commit_sizes, new_commit_sizes, plat, ver
                )
                output_diff(parameters_artifacts, diff_modules)
                modules.extend(diff_modules)
                if quality_gate_threshold:
                    passes_quality_gate = check_quality_gate(
                        app, total_diff[(plat, ver)], old_size[(plat, ver)], quality_gate_threshold, plat, ver
                    )
                if to_dd_org or to_dd_key:
                    from .utils.common_funcs import send_metrics_to_dd

                    send_metrics_to_dd(app, modules, to_dd_org, to_dd_key, to_dd_site, compressed, mode)

        else:
            with GitRepo(repo_url) as gitRepo:
                try:
                    date_str, _, _ = gitRepo.get_commit_metadata(old_commit)
                    date = datetime.strptime(date_str, "%b %d %Y").date()
                    if date < MINIMUM_DATE:
                        raise ValueError(f"First commit must be after {MINIMUM_DATE.strftime('%b %d %Y')} ")

                    for plat, ver in combinations:
                        parameters_repo: CLIParameters = {
                            "app": app,
                            "platform": plat,
                            "py_version": ver,
                            "compressed": compressed,
                            "format": format,
                            "show_gui": show_gui,
                        }
                        (
                            diff_modules,
                            total_diff,
                            old_size,
                        ) = get_diff(
                            gitRepo,
                            old_commit,
                            new_commit,
                            total_diff,
                            old_size,
                            parameters_repo,
                        )
                        output_diff(parameters_repo, diff_modules)
                        modules.extend(diff_modules)
                        if quality_gate_threshold:
                            passes_quality_gate = check_quality_gate(
                                app, total_diff[(plat, ver)], old_size[(plat, ver)], quality_gate_threshold, plat, ver
                            )
                        if to_dd_org or to_dd_key:
                            from .utils.common_funcs import send_metrics_to_dd

                            send_metrics_to_dd(app, modules, to_dd_org, to_dd_key, to_dd_site, compressed, mode)

                except Exception as e:
                    app.abort(str(e))

        if format or not passes_quality_gate:
            modules = [module for module in modules if module["Size_Bytes"] != 0]
            if format:
                from .utils.common_funcs import export_format

                export_format(app, format, modules, "diff", platform, py_version, compressed)
            if quality_gate_threshold and not passes_quality_gate:
                from .utils.common_funcs import save_quality_gate_html

                save_quality_gate_html(
                    app,
                    modules,
                    "diff.html",
                    old_commit,
                    quality_gate_threshold,
                    old_size,
                    total_diff,
                )
        return None


def validate_parameters(
    app: Application,
    old_commit: str | None,
    new_commit: str,
    format: list[str],
    valid_platforms: set[str],
    valid_versions: set[str],
    platform: str | None,
    py_version: str | None,
    to_dd_org: str | None,
    to_dd_key: str | None,
    to_dd_site: str | None,
    use_artifacts: bool,
) -> None:
    errors = []
    if platform and platform not in valid_platforms:
        errors.append(f"Invalid platform: {platform}")

    elif py_version and py_version not in valid_versions:
        errors.append(f"Invalid version: {py_version}")

    if len(new_commit) < MINIMUM_LENGTH_COMMIT and old_commit and len(old_commit) < MINIMUM_LENGTH_COMMIT:
        errors.append(f"Commit hashes must be at least {MINIMUM_LENGTH_COMMIT} characters long")

    elif len(new_commit) < MINIMUM_LENGTH_COMMIT:
        errors.append(
            f"New commit hash must be at least {MINIMUM_LENGTH_COMMIT} characters long.",
        )

    elif old_commit and len(old_commit) < MINIMUM_LENGTH_COMMIT:
        errors.append(
            f"Old commit hash must be at least {MINIMUM_LENGTH_COMMIT} characters long.",
        )

    if use_artifacts:
        if len(new_commit) < FULL_LENGTH_COMMIT:
            errors.append("If --use-artifacts is provided, --new-commit must be a full length commit hash.")

        if old_commit and len(old_commit) < FULL_LENGTH_COMMIT:
            errors.append("If --use-artifacts is provided, --old-commit must be a full length commit hash.")

    if new_commit and old_commit == new_commit:
        errors.append("Commit hashes must be different")

    if format:
        for fmt in format:
            if fmt not in ["png", "csv", "markdown", "json"]:
                errors.append(f"Invalid format: {fmt}. Only png, csv, markdown, json, and html are supported.")

    if to_dd_site and not to_dd_key:
        errors.append("If --to-dd-site is provided, --to-dd-key must also be provided.")

    if to_dd_site and to_dd_org:
        errors.append("If --to-dd-org is provided, --to-dd-site must not be provided.")

    if to_dd_key and to_dd_org:
        errors.append("If --to-dd-org is provided, --to-dd-key must not be provided.")

    if errors:
        app.abort("\n".join(errors))


def get_diff(
    gitRepo: GitRepo,
    old_commit: str,
    new_commit: str,
    total_diff: dict[tuple[str, str], int],
    old_size: dict[tuple[str, str], int],
    params: CLIParameters,
) -> tuple[list[FileDataEntry], dict[tuple[str, str], int], dict[tuple[str, str], int]]:
    files_b, dependencies_b, files_a, dependencies_a = get_repo_info(
        gitRepo, params["platform"], params["py_version"], old_commit, new_commit, params["compressed"]
    )

    (
        integrations,
        integrations_total_diff,
        integrations_old_size,
    ) = calculate_diff(files_b, files_a, params["platform"], params["py_version"])
    (
        dependencies,
        dependencies_total_diff,
        dependencies_old_size,
    ) = calculate_diff(dependencies_b, dependencies_a, params["platform"], params["py_version"])
    total_diff[(params["platform"], params["py_version"])] = integrations_total_diff + dependencies_total_diff
    old_size[(params["platform"], params["py_version"])] = integrations_old_size + dependencies_old_size
    return integrations + dependencies, total_diff, old_size


def output_diff(params: CLIParameters, modules: list[FileDataEntry]) -> None:
    differences = 0
    modules.sort(key=lambda x: abs(x["Size_Bytes"]), reverse=True)
    for module in modules:
        if module["Size_Bytes"] > 0:
            module["Size"] = f"+{module['Size']}"

        if module["Size_Bytes"] != 0:
            differences += 1

    if differences == 0:
        params["app"].display(
            f"No size differences were detected between the selected commits for {params['platform']}"
            f"and Python version {params['py_version']}"
        )
        return

    if not params["format"] or params["format"] == ["png"]:  # if no format is provided for the data print the table
        from .utils.common_funcs import print_table

        print_table(params["app"], "Diff", modules)

    treemap_path = None
    if params["format"] and "png" in params["format"]:
        treemap_path = os.path.join(
            "size_diff_visualizations", f"treemap_{params['platform']}_{params['py_version']}.png"
        )

    if params["show_gui"] or treemap_path:
        from .utils.common_funcs import plot_treemap

        plot_treemap(
            params["app"],
            modules,
            f"Disk Usage Differences for {params['platform']} and Python version {params['py_version']}",
            params["show_gui"],
            "diff",
            treemap_path,
        )


def get_repo_info(
    gitRepo: GitRepo,
    platform: str,
    py_version: str,
    old_commit: str,
    new_commit: str,
    compressed: bool,
) -> tuple[list[FileDataEntry], list[FileDataEntry], list[FileDataEntry], list[FileDataEntry]]:
    """
    Retrieves integration and dependency sizes for two commits in the repo.

    Args:
        gitRepo: An instance of GitRepo for accessing the repository.
        platform: Target platform for dependency resolution.
        version: Python version for dependency resolution.
        old_commit: The earlier commit SHA to compare.
        new_commit: The later commit SHA to compare.
        compressed: Whether to measure compressed sizes.

    Returns:
        A tuple of four lists:
            - files_b: Integration sizes at old_commit
            - dependencies_b: Dependency sizes at old_commit
            - files_a: Integration sizes at new_commit
            - dependencies_a: Dependency sizes at new_commit
    """
    from .utils.common_funcs import get_dependencies, get_files

    repo = gitRepo.repo_dir
    gitRepo.checkout_commit(old_commit)
    files_b = get_files(repo, compressed, py_version, platform)
    dependencies_b = get_dependencies(repo, platform, py_version, compressed)

    gitRepo.checkout_commit(new_commit)
    files_a = get_files(repo, compressed, py_version, platform)
    dependencies_a = get_dependencies(repo, platform, py_version, compressed)

    return files_b, dependencies_b, files_a, dependencies_a


def calculate_diff(
    size_old_commit: list[FileDataEntry], size_new_commit: list[FileDataEntry], platform: str, py_version: str
) -> tuple[list[FileDataEntry], int, int]:
    """
    Computes size differences between two sets of integrations or dependencies.

    Args:
        size_old_commit: Entries from the first (earlier) commit.
        size_new_commit: Entries from the second (later) commit.

    Returns:
        A list of FileDataEntry items representing only the entries with a size difference.
        Entries include new, deleted, or changed modules, with delta size in bytes and human-readable format.
    """
    from .utils.common_funcs import convert_to_human_readable_size

    old_commit = {
        (entry["Name"], entry["Type"], entry["Platform"], entry["Python_Version"]): entry for entry in size_old_commit
    }
    new_commit = {
        (entry["Name"], entry["Type"], entry["Platform"], entry["Python_Version"]): entry for entry in size_new_commit
    }

    all_names = set(old_commit) | set(new_commit)
    diffs: list[FileDataEntry] = []

    total_diff = 0
    old_size = 0

    for name, _type, platform, py_version in all_names:
        old = old_commit.get((name, _type, platform, py_version))
        new = new_commit.get((name, _type, platform, py_version))
        size_old = int(old["Size_Bytes"]) if old else 0
        size_new = int(new["Size_Bytes"]) if new else 0
        delta = size_new - size_old
        percentage = (delta / size_old) * 100 if size_old != 0 else 0
        total_diff += delta
        old_size += size_old
        ver_old = old["Version"] if old else ""
        ver_new = new["Version"] if new else ""

        if size_old == 0:
            change_type = "New"
            name_str = f"{name}"
            version_str = ver_new
        elif size_new == 0:
            change_type = "Removed"
            name_str = f"{name}"
            version_str = ver_old
        elif delta != 0:
            change_type = "Modified"
            name_str = name
            version_str = f"{ver_old} -> {ver_new}" if ver_new != ver_old else ver_new
        else:
            change_type = "Unchanged"
            name_str = name
            version_str = ver_new

        diffs.append(
            {
                "Name": name_str,
                "Version": version_str,
                "Type": _type,
                "Platform": platform,
                "Python_Version": py_version,
                "Size_Bytes": delta,
                "Size": convert_to_human_readable_size(delta),
                "Percentage": round(percentage, 2),
                "Delta_Type": change_type,
            }
        )
    return diffs, total_diff, old_size


def check_quality_gate(
    app: Application, total_diff: int, old_size: int, quality_gate_threshold: int, platform: str, py_version: str
) -> bool:
    percentage = (total_diff / old_size) * 100

    if not (passes := (percentage < quality_gate_threshold)):
        app.display_error(f"Quality gate threshold not passed for {platform} and {py_version}")

    return passes
