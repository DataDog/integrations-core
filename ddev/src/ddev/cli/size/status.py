# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from pathlib import Path

import click

from .common import (
    compress,
    get_dependencies,
    get_dependencies_sizes,
    get_gitignore_files,
    group_modules,
    is_correct_dependency,
    is_valid_integration,
    print_csv,
    print_table,
)

VALID_PLATFORMS = ["linux-aarch64", "linux-x86_64", "macos-x86_64", "windows-x86_64"]
VALID_PYTHON_VERSIONS = ["3.12"]
REPO_PATH = Path(__file__).resolve().parents[5]


@click.command()
@click.option('--platform', type=click.Choice(VALID_PLATFORMS), help="Target platform")
@click.option('--python', 'version', type=click.Choice(VALID_PYTHON_VERSIONS), help="Python version (MAJOR.MINOR)")
@click.option('--compressed', is_flag=True, help="Measure compressed size")
@click.option('--csv', is_flag=True, help="Output in CSV format")
@click.pass_obj
def status(app, platform, version, compressed, csv):
    try:
        platforms = VALID_PLATFORMS if platform is None else [platform]
        versions = VALID_PYTHON_VERSIONS if version is None else [version]

        for i, (plat, ver) in enumerate([(p, v) for p in platforms for v in versions]):
            status_mode(app, plat, ver, compressed, csv, i)
    except Exception as e:
        app.abort(str(e))


def status_mode(app, platform, version, compressed, csv, i):
    if compressed:
        modules = get_compressed_files() + get_compressed_dependencies(platform, version)

        grouped_modules = group_modules(modules, platform, version)
        grouped_modules.sort(key=lambda x: x['Size (Bytes)'], reverse=True)

        if csv:
            print_csv(app, i, grouped_modules)
        else:
            print_table(app, grouped_modules, platform, version)


def get_compressed_files():

    ignored_files = {"datadog_checks_dev", "datadog_checks_tests_helper"}
    git_ignore = get_gitignore_files(REPO_PATH)
    included_folder = "datadog_checks/"

    file_data = []
    for root, _, files in os.walk(REPO_PATH):
        for file in files:
            file_path = os.path.join(root, file)

            # Convert the path to a relative format within the repo
            relative_path = os.path.relpath(file_path, REPO_PATH)

            # Filter files
            if is_valid_integration(relative_path, included_folder, ignored_files, git_ignore):
                compressed_size = compress(file_path)
                integration = relative_path.split(os.sep)[0]
                file_data.append(
                    {
                        "File Path": relative_path,
                        "Type": "Integration",
                        "Name": integration,
                        "Size (Bytes)": compressed_size,
                    }
                )
    return file_data


def get_compressed_dependencies(platform, version):

    resolved_path = os.path.join(REPO_PATH, ".deps/resolved")
    for filename in os.listdir(resolved_path):
        file_path = os.path.join(resolved_path, filename)
        if os.path.isfile(file_path) and is_correct_dependency(platform, version, filename):
            deps, download_urls = get_dependencies(file_path)
            return get_dependencies_sizes(deps, download_urls)
