# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from typing import List, Optional, Tuple, cast

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from ddev.cli.application import Application

from .common import (
    FileDataEntry,
    GitRepo,
    convert_size,
    get_dependencies,
    get_files,
    group_modules,
    plot_treemap,
    print_csv,
    print_table,
    valid_platforms_versions,
)

console = Console()


@click.command()
@click.argument("first_commit")
@click.argument("second_commit")
@click.option(
    '--platform', help="Target platform (e.g. linux-aarch64). If not specified, all platforms will be analyzed"
)
@click.option('--python', 'version', help="Python version (e.g 3.12).  If not specified, all versions will be analyzed")
@click.option('--compressed', is_flag=True, help="Measure compressed size")
@click.option('--csv', is_flag=True, help="Output in CSV format")
@click.option('--save_to_png_path', help="Path to save the treemap as PNG")
@click.option(
    '--show_gui',
    is_flag=True,
    help="Display a pop-up window with a treemap showing size differences between the two commits.",
)
@click.pass_obj
def diff(
    app: Application,
    first_commit: str,
    second_commit: str,
    platform: Optional[str],
    version: Optional[str],
    compressed: bool,
    csv: bool,
    save_to_png_path: str,
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
    ) as progress:
        task = progress.add_task("[cyan]Calculating differences...", total=None)
        if len(first_commit) < 7 and len(second_commit) < 7:
            raise click.BadParameter("Commit hashes must be at least 7 characters long")
        elif len(first_commit) < 7:
            raise click.BadParameter("First commit hash must be at least 7 characters long.", param_hint="first_commit")
        elif len(second_commit) < 7:
            raise click.BadParameter(
                "Second commit hash must be at least 7 characters long.", param_hint="second_commit"
            )
        # if first_commit == second_commit:
        # raise click.BadParameter("Commit hashes must be different")

        repo_url = app.repo.path
        with GitRepo(repo_url) as gitRepo:
            try:
                valid_platforms, valid_versions = valid_platforms_versions(gitRepo.repo_dir)
                if platform and platform not in valid_platforms:
                    raise ValueError(f"Invalid platform: {platform}")
                elif version and version not in valid_versions:
                    raise ValueError(f"Invalid version: {version}")
                if platform is None or version is None:
                    platforms = valid_platforms if platform is None else [platform]
                    versions = valid_versions if version is None else [version]
                    progress.remove_task(task)

                    for i, (plat, ver) in enumerate([(p, v) for p in platforms for v in versions]):
                        path = None
                        if save_to_png_path:
                            base, ext = os.path.splitext(save_to_png_path)
                            path = f"{base}_{plat}_{ver}{ext}"

                        diff_mode(
                            app,
                            gitRepo,
                            first_commit,
                            second_commit,
                            plat,
                            ver,
                            compressed,
                            csv,
                            i,
                            progress,
                            path,
                            show_gui,
                        )
                else:
                    progress.remove_task(task)
                    diff_mode(
                        app,
                        gitRepo,
                        first_commit,
                        second_commit,
                        platform,
                        version,
                        compressed,
                        csv,
                        None,
                        progress,
                        save_to_png_path,
                        show_gui,
                    )

            except Exception as e:
                if progress and progress.tasks:
                    progress.remove_task(task)
                    progress.stop()

                app.abort(str(e))


def diff_mode(
    app: Application,
    gitRepo: GitRepo,
    first_commit: str,
    second_commit: str,
    platform: str,
    version: str,
    compressed: bool,
    csv: bool,
    i: Optional[int],
    progress: Progress,
    save_to_png_path: Optional[str],
    show_gui: bool,
) -> None:
    files_b, dependencies_b, files_a, dependencies_a = get_repo_info(
        gitRepo, platform, version, first_commit, second_commit, compressed, progress
    )

    integrations = get_diff(files_b, files_a, 'Integration')
    dependencies = get_diff(dependencies_b, dependencies_a, 'Dependency')
    if integrations + dependencies == [] and not csv:
        app.display(f"No size differences were detected between the selected commits for {platform}.")
    else:
        grouped_modules = group_modules(integrations + dependencies, platform, version, i)
        grouped_modules.sort(key=lambda x: abs(cast(int, x['Size_Bytes'])), reverse=True)
        for module in grouped_modules:
            if cast(int, module['Size_Bytes']) > 0:
                module['Size'] = f"+{module['Size']}"
        if csv:
            print_csv(app, i, grouped_modules)
        else:
            print_table(app, "Diff", grouped_modules)

        if show_gui or save_to_png_path:
            plot_treemap(
                grouped_modules,
                f"Disk Usage Differences for {platform} and Python version {version}",
                show_gui,
                "diff",
                save_to_png_path,
            )


def get_repo_info(
    gitRepo: GitRepo,
    platform: str,
    version: str,
    first_commit: str,
    second_commit: str,
    compressed: bool,
    progress: Progress,
) -> Tuple[List[FileDataEntry], List[FileDataEntry], List[FileDataEntry], List[FileDataEntry]]:
    with progress:
        repo = gitRepo.repo_dir
        task = progress.add_task("[cyan]Calculating sizes for the first commit...", total=None)
        gitRepo.checkout_commit(first_commit)
        files_b = get_files(repo, compressed)
        dependencies_b = get_dependencies(repo, platform, version, compressed)
        progress.remove_task(task)

        task = progress.add_task("[cyan]Calculating sizes for the second commit...", total=None)
        gitRepo.checkout_commit(second_commit)
        files_a = get_files(repo, compressed)
        dependencies_a = get_dependencies(repo, platform, version, compressed)
        progress.remove_task(task)

    return files_b, dependencies_b, files_a, dependencies_a


def get_diff(
    size_first_commit: List[FileDataEntry], size_second_commit: List[FileDataEntry], type: str
) -> List[FileDataEntry]:

    first_commit = {entry["Name"]: entry for entry in size_first_commit}
    second_commit = {entry["Name"]: entry for entry in size_second_commit}

    all_names = set(first_commit) | set(second_commit)
    diffs: List[FileDataEntry] = []

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
        if a:
            type = a["Type"]
        elif b:
            type = b["Type"]
        else:
            type = ""

        diffs.append(
            {
                "Name": name_str,
                "Version": version_str,
                "Type": type,
                "Size_Bytes": delta,
                "Size": convert_size(delta),
            }
        )

    return diffs
