# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import sys
from pathlib import Path

import click
import requests

from .common import (
    compress,
    get_dependencies,
    get_gitignore_files,
    group_modules,
    is_correct_dependency,
    is_valid_integration,
    print_csv,
    print_table,
)
from .GitRepo import GitRepo

VALID_PLATFORMS = ["linux-aarch64", "linux-x86_64", "macos-x86_64", "windows-x86_64"]
VALID_PYTHON_VERSIONS = ["3.12"]


@click.command()
@click.argument("before")
@click.argument("after")
@click.option('--platform', type=click.Choice(VALID_PLATFORMS), help="Target platform")
@click.option('--python', 'version', type=click.Choice(VALID_PYTHON_VERSIONS), help="Python version (MAJOR.MINOR)")
@click.option('--compressed', is_flag=True, help="Measure compressed size")
@click.option('--csv', is_flag=True, help="Output in CSV format")
@click.pass_obj
def diff(app, before, after, platform, version, compressed, csv):
    platforms = VALID_PLATFORMS if platform is None else [platform]
    versions = VALID_PYTHON_VERSIONS if version is None else [version]

    for i, (plat, ver) in enumerate([(p, v) for p in platforms for v in versions]):
        diff_mode(app, before, after, plat, ver, compressed, csv, i)


def diff_mode(app, before, after, platform, version, compressed, csv, i):
    if compressed:
        with GitRepo("https://github.com/DataDog/integrations-core.git") as gitRepo:
            repo = gitRepo.repo_dir
            gitRepo.checkout_commit(before)
            files_b = get_compressed_files(app, repo)
            dependencies_b = get_compressed_dependencies(app, repo, platform, version)
            gitRepo.checkout_commit(after)
            files_a = get_compressed_files(app, repo)
            dependencies_a = get_compressed_dependencies(app, repo, platform, version)

        integrations = get_diff(files_b, files_a, 'Integration')
        dependencies = get_diff(dependencies_b, dependencies_a, 'Dependency')

        grouped_modules = group_modules(integrations + dependencies, platform, version)
        grouped_modules.sort(key=lambda x: x['Size (Bytes)'], reverse=True)
        for module in grouped_modules:
            if module['Size (Bytes)'] > 0:
                module['Size'] = f"+{module['Size']}"

        if csv:
            print_csv(app, i, grouped_modules)
        else:
            print_table(app, grouped_modules, platform, version)


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


def get_compressed_files(app, repo_path):

    ignored_files = {"datadog_checks_dev", "datadog_checks_tests_helper"}
    git_ignore = get_gitignore_files(app, repo_path)
    included_folder = "datadog_checks/"

    file_data = {}
    for root, _, files in os.walk(repo_path):
        for file in files:
            file_path = os.path.join(root, file)

            # Convert the path to a relative format within the repo
            relative_path = os.path.relpath(file_path, repo_path)

            # Filter files
            if is_valid_integration(relative_path, included_folder, ignored_files, git_ignore):
                compressed_size = compress(app, file_path, relative_path)
                file_data[relative_path] = compressed_size
    return file_data


def get_compressed_dependencies(app, repo_path, platform, version):

    resolved_path = os.path.join(repo_path, ".deps/resolved")

    if not os.path.exists(resolved_path) or not os.path.isdir(resolved_path):
        app.display_error(f"Error: Directory not found {resolved_path}")
        sys.exit(1)

    for filename in os.listdir(resolved_path):
        file_path = os.path.join(resolved_path, filename)

        if os.path.isfile(file_path) and is_correct_dependency(platform, version, filename):
            deps, download_urls = get_dependencies(app, file_path)
            return get_dependencies_sizes(app, deps, download_urls)
    return {}


def get_dependencies_sizes(app, deps, download_urls):
    file_data = {}
    for dep, url in zip(deps, download_urls, strict=False):
        dep_response = requests.head(url)
        if dep_response.status_code != 200:
            app.display_error(f"Error {dep_response.status_code}: Unable to fetch the dependencies file")
            sys.exit(1)
        else:
            size = dep_response.headers.get("Content-Length", None)
            file_data[dep] = int(size)

    return file_data
