# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, cast

import click
import requests
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from ddev.cli.application import Application

from .common import (
    GitRepo,
    compress,
    get_dependencies_list,
    get_gitignore_files,
    group_modules,
    is_correct_dependency,
    is_valid_integration,
    plot_treemap,
    print_csv,
    print_table,
    valid_platforms_versions,
)

console = Console()


@click.command()
@click.argument("before")
@click.argument("after")
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
    before: str,
    after: str,
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
                            before,
                            after,
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
                        before,
                        after,
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
                app.abort(str(e))


def diff_mode(
    app: Application,
    gitRepo: GitRepo,
    before: str,
    after: str,
    platform: str,
    version: str,
    compressed: bool,
    csv: bool,
    i: Optional[int],
    progress: Progress,
    save_to_png_path: str,
    show_gui: bool,
) -> None:
    files_b, dependencies_b, files_a, dependencies_a = get_repo_info(
        gitRepo, platform, version, before, after, compressed, progress
    )

    integrations = get_diff(files_b, files_a, 'Integration')
    dependencies = get_diff(dependencies_b, dependencies_a, 'Dependency')
    if integrations + dependencies == [] and not csv:
        app.display(f"No size differences were detected between the selected commits for {platform}.")

    grouped_modules = group_modules(integrations + dependencies, platform, version, i)
    grouped_modules.sort(key=lambda x: abs(cast(int, x['Size (Bytes)'])), reverse=True)
    for module in grouped_modules:
        if cast(int, module['Size (Bytes)']) > 0:
            module['Size'] = f"+{module['Size']}"
    else:
        if csv:
            print_csv(app, i, grouped_modules)
        elif show_gui or save_to_png_path:
            print_table(app, "Diff", grouped_modules)
            plot_treemap(
                grouped_modules,
                f"Disk Usage Differences for {platform} and Python version {version}",
                show_gui,
                "diff",
                save_to_png_path,
            )
        else:
            print_table(app, "Diff", grouped_modules)


def get_repo_info(
    gitRepo: GitRepo,
    platform: str,
    version: str,
    before: str,
    after: str,
    compressed: bool,
    progress: Progress,
) -> Tuple[Dict[str, int], Dict[str, int], Dict[str, int], Dict[str, int]]:
    with progress:
        repo = gitRepo.repo_dir
        task = progress.add_task("[cyan]Calculating sizes for the first commit...", total=None)
        gitRepo.checkout_commit(before)
        files_b = get_files(repo, compressed)
        dependencies_b = get_dependencies(repo, platform, version, compressed)
        progress.remove_task(task)

        task = progress.add_task("[cyan]Calculating sizes for the second commit...", total=None)
        gitRepo.checkout_commit(after)
        files_a = get_files(repo, compressed)
        dependencies_a = get_dependencies(repo, platform, version, compressed)
        progress.remove_task(task)

    return files_b, dependencies_b, files_a, dependencies_a


def get_diff(size_before: Dict[str, int], size_after: Dict[str, int], type: str) -> List[Dict[str, str | int]]:
    all_paths = set(size_before.keys()) | set(size_after.keys())
    diff_files = []

    for path in all_paths:
        size_b = size_before.get(path, 0)
        size_a = size_after.get(path, 0)
        size_delta = size_a - size_b
        module = Path(path).parts[0]
        if size_delta != 0:
            if size_b == 0:
                diff_files.append(
                    {
                        'File Path': path,
                        'Type': type,
                        'Name': module + " (NEW)",
                        'Size (Bytes)': size_delta,
                    }
                )
            elif size_a == 0:
                diff_files.append(
                    {
                        'File Path': path,
                        'Type': type,
                        'Name': module + " (DELETED)",
                        'Size (Bytes)': size_delta,
                    }
                )
            else:
                diff_files.append(
                    {
                        'File Path': path,
                        'Type': type,
                        'Name': module,
                        'Size (Bytes)': size_delta,
                    }
                )

    return cast(List[Dict[str, str | int]], diff_files)


def get_files(repo_path: str, compressed: bool) -> Dict[str, int]:

    ignored_files = {"datadog_checks_dev", "datadog_checks_tests_helper"}
    git_ignore = get_gitignore_files(repo_path)
    included_folder = "datadog_checks" + os.sep

    file_data = {}
    for root, _, files in os.walk(repo_path):
        for file in files:
            file_path = os.path.join(root, file)

            # Convert the path to a relative format within the repo
            relative_path = os.path.relpath(file_path, repo_path)

            # Filter files
            if is_valid_integration(relative_path, included_folder, ignored_files, git_ignore):
                size = compress(file_path) if compressed else os.path.getsize(file_path)
                file_data[relative_path] = size
    return file_data


def get_dependencies(repo_path: str, platform: str, version: str, compressed: bool) -> Dict[str, int]:

    resolved_path = os.path.join(repo_path, os.path.join(repo_path, ".deps", "resolved"))

    for filename in os.listdir(resolved_path):
        file_path = os.path.join(resolved_path, filename)

        if os.path.isfile(file_path) and is_correct_dependency(platform, version, filename):
            deps, download_urls = get_dependencies_list(file_path)
            return get_dependencies_sizes(deps, download_urls, compressed)
    return {}


def get_dependencies_sizes(deps: List[str], download_urls: List[str], compressed: bool) -> Dict[str, int]:
    file_data = {}
    for dep, url in zip(deps, download_urls, strict=False):
        if compressed:
            response = requests.head(url)
            response.raise_for_status()
            size_str = response.headers.get("Content-Length")
            if size_str is None:
                raise ValueError(f"Missing size for {dep}")
            size = int(size_str)
        else:
            with requests.get(url, stream=True) as response:
                response.raise_for_status()
                wheel_data = response.content

            with tempfile.TemporaryDirectory() as tmpdir:
                wheel_path = Path(tmpdir) / "package.whl"
                with open(wheel_path, "wb") as f:
                    f.write(wheel_data)
                extract_path = Path(tmpdir) / "extracted"
                with zipfile.ZipFile(wheel_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)

                size = 0
                for dirpath, _, filenames in os.walk(extract_path):
                    for name in filenames:
                        file_path = os.path.join(dirpath, name)
                        size += os.path.getsize(file_path)
        file_data[dep] = size
    return file_data
