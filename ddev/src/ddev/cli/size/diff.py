# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING

import click

from ddev.cli.application import Application
from ddev.cli.size.utils.common_params import common_params
from ddev.cli.size.utils.size_model import Sizes
from ddev.utils.fs import Path

if TYPE_CHECKING:
    from ddev.cli.size.utils.common_funcs import CLIParameters, GitRepo
    from ddev.cli.size.utils.size_model import TotalsDict


MINIMUM_DATE = datetime(2024, 9, 17).date()
FULL_LENGTH_COMMIT = 40


@click.command()
@click.argument("commit")
@click.option(
    "--compare-to",
    "baseline",
    help="Commit to compare to.",
)
@click.option(
    "--python", "py_version", help="Python version (e.g 3.12).  If not specified, all versions will be analyzed"
)
@click.option("--use-artifacts", is_flag=True, help="Fetch sizes from GitHub Actions artifacts instead of the repo")
@click.option(
    "--quality-gate-threshold",
    type=float,
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
@click.pass_context
def diff(
    ctx: click.Context,
    commit: str,
    baseline: str | None,
    platform: str | None,
    py_version: str | None,
    compressed: bool,
    format: list[str],
    show_gui: bool,
    use_artifacts: bool,
    quality_gate_threshold: float | None,
    to_dd_org: str | None,
    to_dd_key: str | None,
    to_dd_site: str | None,
) -> None:
    """
    Compares the size of integrations and dependencies between COMMIT and the comparisson point defined based on the
    value of the `--compare-to` option:

        - If `--compare-to` is provided, it will be used as the diff source
        - If `--compare-to` is not provided, the source will be the merge base with master, if the command is run from
          a feature branch, or the previous commit if the command is run in the master branch.

    Both COMMIT and the value of `--compare-to` need to be the full commit sha.
    """

    from .utils.common_funcs import (
        get_valid_platforms,
        get_valid_versions,
    )

    app: Application = ctx.obj

    with app.status("Calculating differences..."):
        diff_sizes: Sizes = Sizes([])

        valid_versions = get_valid_versions(app.repo.path)
        valid_platforms = get_valid_platforms(app.repo.path, valid_versions)
        validate_parameters(
            app,
            baseline,
            commit,
            valid_platforms,
            valid_versions,
            platform,
            py_version,
            to_dd_org,
            to_dd_key,
            to_dd_site,
        )

        platforms = valid_platforms if platform is None else [platform]
        versions = valid_versions if py_version is None else [py_version]
        combinations = [(p, v) for p in platforms for v in versions]

        if not baseline:
            from ddev.cli.size.utils.gha_artifacts import get_previous_commit

            baseline = get_previous_commit(app, commit)
            if not baseline:
                app.abort("No baseline commit found")
            app.display(f"Comparing to commit: {baseline}")

        parameters: CLIParameters = {
            "app": app,
            "combinations": combinations,
            "compressed": compressed,
            "format": format,
            "show_gui": show_gui,
            "quality_gate_threshold": quality_gate_threshold,
            "to_dd_org": to_dd_org,
            "to_dd_key": to_dd_key,
            "to_dd_site": to_dd_site,
        }

        if use_artifacts:
            diff_sizes, baseline_total_size, commit_total_size, passes_quality_gate = get_diff_from_artifacts(
                app, baseline, commit, parameters
            )
        else:
            diff_sizes, baseline_total_size, commit_total_size, passes_quality_gate = get_diff_from_repo(
                app, baseline, commit, parameters
            )

        if format or quality_gate_threshold:
            filtered_diffs = diff_sizes.filter_no_zero()

            if format:
                from .utils.common_funcs import SizeMode, export_format

                export_format(app, format, filtered_diffs, SizeMode.DIFF, compressed)

            if quality_gate_threshold:
                from ddev.cli.size.utils.export_quality_gates import (
                    save_quality_gate_html,
                    save_quality_gate_html_table,
                )

                save_quality_gate_html(
                    app,
                    filtered_diffs,
                    compressed,
                    Path("diff.html"),
                    baseline,
                    quality_gate_threshold,
                    baseline_total_size,
                    filtered_diffs._total_sizes,
                    passes_quality_gate,
                )
                save_quality_gate_html_table(
                    app,
                    filtered_diffs,
                    compressed,
                    Path("diff_table.html"),
                    baseline,
                    quality_gate_threshold,
                    baseline_total_size,
                    commit_total_size,
                    filtered_diffs._total_sizes,
                    passes_quality_gate,
                )
        if quality_gate_threshold and not passes_quality_gate:
            app.display_error("Quality gate threshold not passed")
            ctx.exit(2)

        return None


def validate_parameters(
    app: Application,
    baseline: str | None,
    commit: str,
    valid_platforms: set[str],
    valid_versions: set[str],
    platform: str | None,
    py_version: str | None,
    to_dd_org: str | None,
    to_dd_key: str | None,
    to_dd_site: str | None,
) -> None:
    errors = []
    if platform and platform not in valid_platforms:
        errors.append(f"Invalid platform: {platform}")

    if py_version and py_version not in valid_versions:
        errors.append(f"Invalid version: {py_version}")

    if len(commit) < FULL_LENGTH_COMMIT or (baseline and len(baseline) < FULL_LENGTH_COMMIT):
        errors.append(f"Commit hashes must be at least {FULL_LENGTH_COMMIT} characters long")

    if baseline == commit:
        errors.append("Commit hashes must be different")

    if to_dd_site and not to_dd_key:
        errors.append("If --to-dd-site is provided, --to-dd-key must also be provided.")

    if to_dd_site and to_dd_org:
        errors.append("If --to-dd-org is provided, --to-dd-site must not be provided.")

    if to_dd_key and to_dd_org:
        errors.append("If --to-dd-org is provided, --to-dd-key must not be provided.")

    if errors:
        app.abort("\n".join(errors))


def get_diff_from_artifacts(
    app: Application, baseline: str, commit: str, params: CLIParameters
) -> tuple[Sizes, TotalsDict, TotalsDict, bool]:
    from ddev.cli.size.utils.gha_artifacts import get_status_sizes_from_commit

    compressed = params["compressed"]
    quality_gate_threshold = params["quality_gate_threshold"]
    to_dd_org = params["to_dd_org"]
    to_dd_key = params["to_dd_key"]
    to_dd_site = params["to_dd_site"]

    artifacts_sizes = Sizes([])
    passes_quality_gate = True

    try:
        baseline_sizes = get_status_sizes_from_commit(app, baseline, compressed)
        commit_sizes = get_status_sizes_from_commit(app, commit, compressed)
    except Exception:
        import traceback

        app.abort(traceback.format_exc())

    if not baseline_sizes:
        app.abort(f"Failed to get sizes for {baseline=}")
    if not commit_sizes:
        app.abort(f"Failed to get sizes for {commit=}")

    for plat, ver in params["combinations"]:
        diff_sizes = commit_sizes.filter(platform=plat, python_version=ver).diff(
            baseline_sizes.filter(platform=plat, python_version=ver)
        )

        params["platform"] = plat
        params["py_version"] = ver
        output_diff(params, baseline, commit, diff_sizes)
        artifacts_sizes = artifacts_sizes + diff_sizes
        if quality_gate_threshold:
            passes_quality_gate = (
                check_quality_gate(
                    app,
                    diff_sizes._total_sizes[plat][ver],
                    baseline_sizes._total_sizes[plat][ver],
                    quality_gate_threshold,
                    plat,
                    ver,
                )
                and passes_quality_gate
            )
        if to_dd_org or to_dd_key:
            from .utils.common_funcs import SizeMode, send_metrics_to_dd

            send_metrics_to_dd(
                app,
                diff_sizes,
                to_dd_org,
                to_dd_key,
                to_dd_site,
                compressed,
                SizeMode.DIFF,
            )

    return artifacts_sizes, baseline_sizes._total_sizes, commit_sizes._total_sizes, passes_quality_gate


def get_diff_from_repo(
    app: Application, baseline: str, commit: str, params: CLIParameters
) -> tuple[Sizes, TotalsDict, TotalsDict, bool]:
    from .utils.common_funcs import GitRepo

    compressed = params["compressed"]
    quality_gate_threshold = params["quality_gate_threshold"]
    to_dd_org = params["to_dd_org"]
    to_dd_key = params["to_dd_key"]
    to_dd_site = params["to_dd_site"]

    with GitRepo(app.repo.path) as gitRepo:
        try:
            date_str, _, _ = gitRepo.get_commit_metadata(baseline)
            date = datetime.strptime(date_str, "%b %d %Y").date()
            if date < MINIMUM_DATE:
                raise ValueError(f"First commit must be after {MINIMUM_DATE.strftime('%b %d %Y')} ")

            repo_sizes = Sizes([])
            passes_quality_gate = True
            baseline_total_size: TotalsDict = defaultdict(lambda: defaultdict(int))
            commit_total_size: TotalsDict = defaultdict(lambda: defaultdict(int))

            for plat, ver in params["combinations"]:
                files_b, dependencies_b, files_c, dependencies_c = get_repo_info(
                    app, gitRepo, plat, ver, baseline, commit, compressed
                )

                diff_sizes = files_c.diff(files_b) + dependencies_c.diff(dependencies_b)
                baseline_total_size[plat][ver] += (
                    files_b._total_sizes[plat][ver] + dependencies_b._total_sizes[plat][ver]
                )
                commit_total_size[plat][ver] += files_c._total_sizes[plat][ver] + dependencies_c._total_sizes[plat][ver]

                params["platform"] = plat
                params["py_version"] = ver
                output_diff(params, baseline, commit, diff_sizes)
                repo_sizes = repo_sizes + diff_sizes
                if quality_gate_threshold:
                    passes_quality_gate = (
                        check_quality_gate(
                            app,
                            diff_sizes._total_sizes[plat][ver],
                            baseline_total_size[plat][ver],
                            quality_gate_threshold,
                            plat,
                            ver,
                        )
                        and passes_quality_gate
                    )
                if to_dd_org or to_dd_key:
                    from .utils.common_funcs import SizeMode, send_metrics_to_dd

                    send_metrics_to_dd(
                        app,
                        diff_sizes,
                        to_dd_org,
                        to_dd_key,
                        to_dd_site,
                        compressed,
                        SizeMode.DIFF,
                    )

        except Exception:
            import traceback

            app.abort(traceback.format_exc())

    return repo_sizes, baseline_total_size, commit_total_size, passes_quality_gate


def output_diff(params: CLIParameters, baseline: str, commit: str, sizes: Sizes) -> None:
    platform = params["platform"]
    py_version = params["py_version"]
    format = params["format"]
    show_gui = params["show_gui"]
    app = params["app"]

    differences = sizes.len_non_zero()
    sizes.sort()

    if differences == 0:
        app.display(
            f"No size differences were detected between the selected commits for {platform}"
            f" and Python version {py_version}"
        )
        return

    if not format or format == ["png"]:  # if no format is provided for the data print the table
        sizes.print_table(
            app,
            f"Disk Usage Differences between {baseline} and {commit} for {platform} and Python version {py_version}",
        )

    treemap_path = None
    if format and "png" in format:
        treemap_path = os.path.join("size_diff_visualizations", f"treemap_{platform}_{py_version}.png")

    if show_gui or treemap_path:
        from .utils.common_funcs import SizeMode, plot_treemap

        plot_treemap(
            app,
            sizes,
            f"Disk Usage Differences for {platform} and Python version {py_version}",
            show_gui,
            SizeMode.DIFF,
            treemap_path,
        )


def get_repo_info(
    app: Application,
    gitRepo: GitRepo,
    platform: str,
    py_version: str,
    baseline: str,
    commit: str,
    compressed: bool,
) -> tuple[Sizes, Sizes, Sizes, Sizes]:
    """
    Retrieves integration and dependency sizes for two commits in the repo.

    Args:
        gitRepo: An instance of GitRepo for accessing the repository.
        platform: Target platform for dependency resolution.
        version: Python version for dependency resolution.
        baseline: The earlier commit SHA to compare.
        commit: The later commit SHA to compare.
        compressed: Whether to measure compressed sizes.

    Returns:
        A tuple of four lists:
            - files_b: Integration sizes at baseline
            - dependencies_b: Dependency sizes at baseline
            - files_a: Integration sizes at commit
            - dependencies_a: Dependency sizes at commit
    """
    from .utils.common_funcs import get_dependencies, get_files

    repo = gitRepo.repo_dir
    gitRepo.checkout_commit(baseline)
    files_b = get_files(repo, compressed, py_version, platform)
    dependencies_b = get_dependencies(app, repo, platform, py_version, compressed)

    gitRepo.checkout_commit(commit)
    files_c = get_files(repo, compressed, py_version, platform)
    dependencies_c = get_dependencies(app, repo, platform, py_version, compressed)

    return files_b, dependencies_b, files_c, dependencies_c


def check_quality_gate(
    app: Application, total_diff: int, old_size: int, quality_gate_threshold: float, platform: str, py_version: str
) -> bool:
    percentage = (total_diff / old_size) * 100

    if not (passes := (percentage < quality_gate_threshold)):
        app.display_error(f"Quality gate threshold not passed for {platform} and {py_version}")

    return passes
