# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from pathlib import Path
from rich.console import Console
import click
import requests
import tempfile
import zipfile
from .common import (
    compress,
    valid_platforms_versions,
    get_dependencies_list,
    get_gitignore_files,
    group_modules,
    is_correct_dependency,
    is_valid_integration,
    print_csv,
    print_table,
    GitRepo
)

# VALID_PLATFORMS, VALID_PYTHON_VERSIONS = valid_platforms_versions()
console = Console()


@click.command()
@click.argument("before")
@click.argument("after")
@click.option('--platform', help="Target platform")
@click.option('--python', 'version', help="Python version (MAJOR.MINOR)")
@click.option('--compressed', is_flag=True, help="Measure compressed size")
@click.option('--csv', is_flag=True, help="Output in CSV format")
@click.pass_obj
def diff(app, before, after, platform, version, compressed, csv):
    repo_url = app.repo.path
    with GitRepo(repo_url) as gitRepo:
        try:
            valid_platforms,valid_versions = valid_platforms_versions(gitRepo.repo_dir)
            if platform and platform not in valid_platforms:
                raise ValueError(f"Invalid platform: {platform}")
            elif version and version not in valid_versions:
                raise ValueError(f"Invalid version: {version}")
            if platform is None or version is None:
                platforms = valid_platforms if platform is None else [platform]
                versions = valid_versions if version is None else [version]

                for i, (plat, ver) in enumerate([(p, v) for p in platforms for v in versions]):
                    diff_mode(app, gitRepo, before, after, plat, ver, compressed, csv, i)
            else:
                    diff_mode(app, gitRepo, before, after, platform, version, compressed, csv, None)

        except Exception as e:
            app.abort(str(e))


def diff_mode(app, gitRepo, before, after, platform, version, compressed, csv, i):
    files_b, dependencies_b, files_a, dependencies_a = get_repo_info(gitRepo, platform, version, before, after, compressed)

    integrations = get_diff(files_b, files_a, 'Integration')
    dependencies = get_diff(dependencies_b, dependencies_a, 'Dependency')
    grouped_modules = group_modules(integrations + dependencies, platform, version, i)
    grouped_modules.sort(key=lambda x: abs(x['Size (Bytes)']), reverse=True)
    for module in grouped_modules:
        if module['Size (Bytes)'] > 0:
            module['Size'] = f"+{module['Size']}"
    if grouped_modules == []:
        app.display("No size differences were detected between the selected commits.")
    else:
        if csv:
            print_csv(app, i, grouped_modules)
        else:
            print_table(app, "Diff", grouped_modules)


def get_repo_info(gitRepo, platform, version, before, after, compressed):
    repo = gitRepo.repo_dir
    with console.status("[cyan]Calculating compressed sizes for the first commit...", spinner="dots"):
        gitRepo.checkout_commit(before)
        files_b = get_files(repo, compressed)
        dependencies_b = get_dependencies(repo, platform, version, compressed)

    with console.status("[cyan]Calculating compressed sizes for the second commit...", spinner="dots"):
        gitRepo.checkout_commit(after)
        files_a = get_files(repo, compressed)
        dependencies_a = get_dependencies(repo, platform, version, compressed)

    return files_b, dependencies_b, files_a, dependencies_a


def get_diff(size_before, size_after, type):
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

    return diff_files


def get_files(repo_path, compressed):

    ignored_files = {"datadog_checks_dev", "datadog_checks_tests_helper"}
    git_ignore = get_gitignore_files(repo_path)
    included_folder = "datadog_checks/"

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


def get_dependencies(repo_path, platform, version, compressed):

    resolved_path = os.path.join(repo_path, ".deps/resolved")

    for filename in os.listdir(resolved_path):
        file_path = os.path.join(resolved_path, filename)

        if os.path.isfile(file_path) and is_correct_dependency(platform, version, filename):
            deps, download_urls = get_dependencies_list(file_path)
            return get_dependencies_sizes(deps, download_urls, compressed)
    return {}


def get_dependencies_sizes(deps, download_urls, compressed):
    file_data = {}
    for dep, url in zip(deps, download_urls):
        if compressed:
            with requests.get(url, stream=True) as response:
                response.raise_for_status()
                size = int(response.headers.get("Content-Length"))
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


