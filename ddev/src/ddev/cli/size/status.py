# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from pathlib import Path
from typing import Dict, List, Optional, Union, cast

import click
from rich.console import Console

from ddev.cli.application import Application

from .common import (
    compress,
    get_dependencies_list,
    get_dependencies_sizes,
    get_gitignore_files,
    group_modules,
    is_correct_dependency,
    is_valid_integration,
    plot_treemap,
    print_csv,
    print_table,
    valid_platforms_versions,
)

# REPO_PATH = Path(__file__).resolve().parents[5]

console = Console()


@click.command()
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
    help="Display a pop-up window with a treemap showing the current size distribution of modules.",
)
@click.pass_obj
def status(
    app: Application,
    platform: Optional[str],
    version: Optional[str],
    compressed: bool,
    csv: bool,
    save_to_png_path: str,
    show_gui: bool,
) -> None:
    """
    Show the current size of all integrations and dependencies.
    """
    try:
        repo_path = app.repo.path
        valid_platforms, valid_versions = valid_platforms_versions(repo_path)
        if platform and platform not in valid_platforms:
            raise ValueError(f"Invalid platform: {platform}")
        elif version and version not in valid_versions:
            raise ValueError(f"Invalid version: {version}")
        if platform is None or version is None:
            platforms = valid_platforms if platform is None else [platform]
            versions = valid_versions if version is None else [version]
            for i, (plat, ver) in enumerate([(p, v) for p in platforms for v in versions]):
                if save_to_png_path:
                    base, ext = os.path.splitext(save_to_png_path)
                    save_to_png_path = f"{base}_{plat}_{ver}{ext}"
                status_mode(app, repo_path, plat, ver, compressed, csv, i, save_to_png_path, show_gui)
        else:
            status_mode(app, repo_path, platform, version, compressed, csv, None, save_to_png_path, show_gui)

    except Exception as e:
        app.abort(str(e))


def status_mode(
    app: Application,
    repo_path: Path,
    platform: str,
    version: str,
    compressed: bool,
    csv: bool,
    i: Optional[int],
    save_to_png_path: str,
    show_gui: bool,
) -> None:
    with console.status("[cyan]Calculating sizes...", spinner="dots"):
        modules = get_files(compressed, repo_path) + get_dependencies(repo_path, platform, version, compressed)
    grouped_modules = group_modules(modules, platform, version, i)
    grouped_modules.sort(key=lambda x: x['Size (Bytes)'], reverse=True)

    if csv:
        print_csv(app, i, grouped_modules)
    elif show_gui or save_to_png_path:
        print_table(app, "Status", grouped_modules)
        plot_treemap(
            grouped_modules,
            f"Disk Usage Status for {platform} and Python version {version}",
            show_gui,
            "status",
            save_to_png_path,
        )
    else:
        print_table(app, "Status", grouped_modules)


def get_files(compressed: bool, repo_path: Path) -> List[Dict[str, Union[str, int]]]:

    ignored_files = {"datadog_checks_dev", "datadog_checks_tests_helper"}
    git_ignore = get_gitignore_files(repo_path)
    included_folder = "datadog_checks" + os.sep

    file_data = []
    for root, _, files in os.walk(repo_path):
        for file in files:
            file_path = os.path.join(root, file)

            # Convert the path to a relative format within the repo
            relative_path = os.path.relpath(file_path, repo_path)

            # Filter files
            if is_valid_integration(relative_path, included_folder, ignored_files, git_ignore):
                size = compress(file_path) if compressed else os.path.getsize(file_path)
                integration = relative_path.split(os.sep)[0]
                file_data.append(
                    {
                        "File Path": relative_path,
                        "Type": "Integration",
                        "Name": integration,
                        "Size (Bytes)": int(size),
                    }
                )
    return cast(List[Dict[str, Union[str, int]]], file_data)


def get_dependencies(
    repo_path: Path, platform: str, version: str, compressed: bool
) -> List[Dict[str, Union[str, int]]]:

    resolved_path = os.path.join(repo_path, os.path.join(repo_path, ".deps", "resolved"))
    for filename in os.listdir(resolved_path):
        file_path = os.path.join(resolved_path, filename)
        if os.path.isfile(file_path) and is_correct_dependency(platform, version, filename):
            deps, download_urls = get_dependencies_list(file_path)
            return get_dependencies_sizes(deps, download_urls, compressed)
    return []
