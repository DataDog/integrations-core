# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
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


@click.command()
@click.argument("new_commit")
@click.option(
    "--compare-to",
    "old_commit",
    help="Commit to compare to. If not specified, will compare to the previous commit on master",
)
@click.option("--python", "version", help="Python version (e.g 3.12).  If not specified, all versions will be analyzed")
@click.option("--use-artifacts", is_flag=True, help="Fetch sizes from gha artifacts instead of the repo")
@click.option(
    "--quality-gate-threshold",
    type=int,
    help="Threshold for the size difference. Outputs the html only if the size"
    " difference is greater than the quality gate threshold",
)
@click.option("--to-dd-org", type=str, help="Send metrics to Datadog using the specified organization name.")
@common_params  # platform, compressed, format, show_gui
@click.pass_obj
def diff(
    app: Application,
    new_commit: str,
    old_commit: str | None,
    platform: str | None,
    version: str | None,
    compressed: bool,
    format: list[str],
    show_gui: bool,
    use_artifacts: bool,
    quality_gate_threshold: int | None,
    to_dd_org: str | None,
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
        validate_parameters(app, old_commit, new_commit, format, valid_platforms, valid_versions, platform, version)

        platforms = valid_platforms if platform is None else [platform]
        versions = valid_versions if version is None else [version]
        combinations = [(p, v) for p in platforms for v in versions]

        if not old_commit:
            old_commit = app.repo.git.merge_base(new_commit, "origin/master")
        if use_artifacts:
            for plat, ver in combinations:
                parameters_artifacts: CLIParameters = {
                    "app": app,
                    "platform": plat,
                    "version": ver,
                    "compressed": compressed,
                    "format": format,
                    "show_gui": show_gui,
                }

                try:
                    old_commit_sizes = get_sizes_from_artifacts(app, old_commit, plat, compressed, "csv")
                    new_commit_sizes = get_sizes_from_artifacts(app, new_commit, plat, compressed, "json")
                except Exception as e:
                    app.abort(str(e))

                diff_modules = calculate_diff(old_commit_sizes, new_commit_sizes, plat, ver)
                output_diff(parameters_artifacts, diff_modules)
                modules.extend(diff_modules)
                total_diff = sum(int(x.get("Size_Bytes", 0)) for x in diff_modules)
                if quality_gate_threshold and total_diff > quality_gate_threshold:
                    passes_quality_gate = False

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
                            "version": ver,
                            "compressed": compressed,
                            "format": format,
                            "show_gui": show_gui,
                        }
                        diff_modules = get_diff(
                            gitRepo,
                            old_commit,
                            new_commit,
                            parameters_repo,
                        )
                        output_diff(parameters_repo, diff_modules)
                        modules.extend(diff_modules)
                        total_diff = sum(int(x.get("Size_Bytes", 0)) for x in diff_modules)
                        if quality_gate_threshold and total_diff > quality_gate_threshold:
                            passes_quality_gate = False
                except Exception as e:
                    app.abort(str(e))

        if to_dd_org:
            from .utils.common_funcs import send_metrics_to_dd
            mode: Literal["diff"] = "diff"
            send_metrics_to_dd(app, modules, to_dd_org, compressed, mode)

        if format or not passes_quality_gate:
            modules = [module for module in modules if module["Size_Bytes"] != 0]
            if format:
                from .utils.common_funcs import export_format

                export_format(app, format, modules, "diff", platform, version, compressed)
            if not passes_quality_gate:
                from .utils.common_funcs import save_html

                save_html(app, "Diff", modules, "diff.html")
        return None


def validate_parameters(
    app: Application,
    old_commit: str | None,
    new_commit: str,
    format: list[str],
    valid_platforms: set[str],
    valid_versions: set[str],
    platform: str | None,
    version: str | None,
):
    errors = []
    if platform and platform not in valid_platforms:
        errors.append(f"Invalid platform: {platform}")
    elif version and version not in valid_versions:
        errors.append(f"Invalid version: {version}")
    if len(new_commit) < MINIMUM_LENGTH_COMMIT and old_commit and len(old_commit) < MINIMUM_LENGTH_COMMIT:
        errors.append(f"Commit hashes must be at least {MINIMUM_LENGTH_COMMIT} characters long")
    elif len(new_commit) < MINIMUM_LENGTH_COMMIT:
        errors.append(
            f"First commit hash must be at least {MINIMUM_LENGTH_COMMIT} characters long.",
        )
    elif new_commit and len(new_commit) < MINIMUM_LENGTH_COMMIT:
        errors.append(
            f"Second commit hash must be at least {MINIMUM_LENGTH_COMMIT} characters long.",
        )
    if new_commit and old_commit == new_commit:
        errors.append("Commit hashes must be different")
    if format:
        for fmt in format:
            if fmt not in ["png", "csv", "markdown", "json"]:
                errors.append(f"Invalid format: {fmt}. Only png, csv, markdown, json, and html are supported.")
    if errors:
        app.abort("\n".join(errors))


def get_sizes_from_artifacts(
    app: Application, commit: str, platform: str, compressed: bool, extension: str | None = "json"
) -> list[FileDataEntry]:
    import tempfile

    from .utils.common_funcs import get_sizes_json_from_artifacts

    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Temporary directory: {temp_dir}")
        sizes_json = get_sizes_json_from_artifacts(commit, platform, temp_dir, compressed, extension)
        compression = "compressed" if compressed else "uncompressed"
        if not sizes_json[compression]:
            app.abort(f"Sizes not found for {commit=}, {platform=}, {compressed=}")
            return []
        if extension == "json" and sizes_json[compression]:
            modules_json: list[FileDataEntry] = list(json.loads(sizes_json[compression].read_text()))
            return modules_json
        elif extension == "csv" and sizes_json[compression]:
            # Assume CSV
            import csv

            modules_csv: list[FileDataEntry] = []
            with open(sizes_json[compression], newline="", encoding="utf-8") as csvfile:
                modules_csv = list(csv.DictReader(csvfile))

            return modules_csv
        return []


def get_diff(
    gitRepo: GitRepo,
    old_commit: str,
    new_commit: str,
    params: CLIParameters,
) -> list[FileDataEntry]:
    files_b, dependencies_b, files_a, dependencies_a = get_repo_info(
        gitRepo, params["platform"], params["version"], old_commit, new_commit, params["compressed"]
    )

    integrations = calculate_diff(files_b, files_a, params["platform"], params["version"])
    dependencies = calculate_diff(dependencies_b, dependencies_a, params["platform"], params["version"])

    return integrations + dependencies


def output_diff(params: CLIParameters, modules: list[FileDataEntry]):
    if modules == []:
        params["app"].display(
            f"No size differences were detected between the selected commits for {params['platform']}"
        )
        return []
    else:
        modules.sort(key=lambda x: abs(x["Size_Bytes"]), reverse=True)
        for module in modules:
            if module["Size_Bytes"] > 0:
                module["Size"] = f"+{module['Size']}"

    if not params["format"] or params["format"] == ["png"]:  # if no format is provided for the data print the table
        from .utils.common_funcs import print_table

        print_table(params["app"], "Diff", modules)

    treemap_path = None
    if params["format"] and "png" in params["format"]:
        treemap_path = os.path.join("size_diff_visualizations", f"treemap_{params['platform']}_{params['version']}.png")

    if params["show_gui"] or treemap_path:
        from .utils.common_funcs import plot_treemap

        plot_treemap(
            params["app"],
            modules,
            f"Disk Usage Differences for {params['platform']} and Python version {params['version']}",
            params["show_gui"],
            "diff",
            treemap_path,
        )


def get_repo_info(
    gitRepo: GitRepo,
    platform: str,
    version: str,
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
    files_b = get_files(repo, compressed, version, platform)
    dependencies_b = get_dependencies(repo, platform, version, compressed)

    gitRepo.checkout_commit(new_commit)
    files_a = get_files(repo, compressed, version, platform)
    dependencies_a = get_dependencies(repo, platform, version, compressed)

    return files_b, dependencies_b, files_a, dependencies_a


def calculate_diff(
    size_old_commit: list[FileDataEntry], size_new_commit: list[FileDataEntry], platform: str, py_version: str
) -> list[FileDataEntry]:
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

    for name, _type, platform, py_version in all_names:
        b = old_commit.get((name, _type, platform, py_version))
        a = new_commit.get((name, _type, platform, py_version))

        size_b = int(b["Size_Bytes"]) if b else 0
        size_a = int(a["Size_Bytes"]) if a else 0
        delta = size_a - size_b

        ver_b = b["Version"] if b else ""
        ver_a = a["Version"] if a else ""

        if size_b == 0:
            change_type = "New"
            name_str = f"{name}"
            version_str = ver_a
        elif size_a == 0:
            change_type = "Removed"
            name_str = f"{name}"
            version_str = ver_b
        else:
            change_type = "Modified"
            name_str = name
            version_str = f"{ver_b} -> {ver_a}" if ver_a != ver_b else ver_a

        diffs.append(
            {
                "Name": name_str,
                "Version": version_str,
                "Type": _type,
                "Platform": platform,
                "Python_Version": py_version,
                "Size_Bytes": delta,
                "Size": convert_to_human_readable_size(delta),
                "Change_Type": change_type,
            }
        )

    return diffs
