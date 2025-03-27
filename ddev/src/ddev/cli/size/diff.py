# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import shutil
import subprocess
import tempfile
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
    try:
        platforms = VALID_PLATFORMS if platform is None else [platform]
        versions = VALID_PYTHON_VERSIONS if version is None else [version]

        for i, (plat, ver) in enumerate([(p, v) for p in platforms for v in versions]):
            diff_mode(app, before, after, plat, ver, compressed, csv, i)
    except Exception as e:
        app.abort(str(e))


def diff_mode(app, before, after, platform, version, compressed, csv, i):
    url = "https://github.com/DataDog/integrations-core.git"
    if compressed:
        files_b, dependencies_b, files_a, dependencies_a = get_repo_info(url, platform, version, before, after)

        integrations = get_diff(files_b, files_a, 'Integration')
        dependencies = get_diff(dependencies_b, dependencies_a, 'Dependency')
        grouped_modules = group_modules(integrations + dependencies, platform, version)
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
                print_table(app, grouped_modules, platform, version)


def get_repo_info(repo_url, platform, version, before, after):
    with GitRepo(repo_url) as gitRepo:
        repo = gitRepo.repo_dir

        gitRepo.checkout_commit(before)
        files_b = get_compressed_files(repo)
        dependencies_b = get_compressed_dependencies(repo, platform, version)

        gitRepo.checkout_commit(after)
        files_a = get_compressed_files(repo)
        dependencies_a = get_compressed_dependencies(repo, platform, version)

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


def get_compressed_files(repo_path):

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
                compressed_size = compress(file_path)
                file_data[relative_path] = compressed_size
    return file_data


def get_compressed_dependencies(repo_path, platform, version):

    resolved_path = os.path.join(repo_path, ".deps/resolved")

    for filename in os.listdir(resolved_path):
        file_path = os.path.join(resolved_path, filename)

        if os.path.isfile(file_path) and is_correct_dependency(platform, version, filename):
            deps, download_urls = get_dependencies(file_path)
            return get_dependencies_sizes(deps, download_urls)
    return {}


def get_dependencies_sizes(deps, download_urls):
    file_data = {}
    for dep, url in zip(deps, download_urls, strict=False):
        dep_response = requests.head(url)
        dep_response.raise_for_status()
        size = dep_response.headers.get("Content-Length", None)
        file_data[dep] = int(size)

    return file_data


class GitRepo:
    def __init__(self, url):
        self.url = url
        self.repo_dir = None

    def __enter__(self):
        self.repo_dir = tempfile.mkdtemp()
        self._run("git init --quiet")
        self._run(f"git remote add origin {self.url}")
        return self

    def _run(self, cmd):
        subprocess.run(
            cmd,
            shell=True,
            cwd=self.repo_dir,
            check=True,
        )

    def checkout_commit(self, commit):
        self._run(f"git fetch --quiet --depth 1 origin {commit}")
        self._run(f"git checkout --quiet {commit}")

    def __exit__(self, exception_type, exception_value, exception_traceback):
        if self.repo_dir and os.path.exists(self.repo_dir):
            shutil.rmtree(self.repo_dir)
