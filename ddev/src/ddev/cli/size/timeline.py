import os
import re
import tempfile
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

import click
import requests
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from ddev.cli.application import Application

from .common import (
    GitRepo,
    WrongDependencyFormat,
    compress,
    convert_size,
    get_gitignore_files,
    is_correct_dependency,
    is_valid_integration,
    print_csv,
    print_table,
    valid_platforms_versions,
)

DEPENDENCY_FILE_CHANGE = datetime.strptime("Sep 17 2024", "%b %d %Y").date()
MINIMUM_DATE = datetime.strptime("Apr 3 2024", "%b %d %Y").date()
console = Console()


@click.command()
@click.argument('type', type=click.Choice(['integration', 'dependency']))
@click.argument('name')
@click.argument('initial', required=False)
@click.argument('final', required=False)
@click.option(
    '--time',
    help="Filter commits starting from a specific date. Accepts both absolute and relative formats, "
    "such as '2025-03-01', '2 weeks ago', or 'yesterday'",
)
@click.option('--threshold', help="Only show modules with size differences greater than a threshold in bytes")
@click.option(
    '--platform',
    help="Target platform to analyze. Only required for dependencies. If not specified, all platforms will be analyzed",
)
@click.option('--compressed', is_flag=True, help="Measure compressed size")
@click.option('--csv', is_flag=True, help="Output results in CSV format")
@click.pass_obj
def timeline(
    app: Application,
    type: str,
    name: str,
    initial: Optional[str],
    final: Optional[str],
    time: Optional[str],
    threshold: Optional[str],
    platform: Optional[str],
    compressed: bool,
    csv: bool,
) -> None:
    """
    Show the size evolution of a module (integration or dependency) over time.
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        transient=True,
    ) as progress:
        module = name  # module is the name of the integration or the dependency
        task = progress.add_task("[cyan]Calculating timeline...", total=None)
        url = app.repo.path
        with GitRepo(url) as gitRepo:
            try:
                # with console.status("[cyan]Fetching commits...", spinner="dots"):
                folder = module if type == 'integration' else '.deps/resolved'
                commits = gitRepo.get_module_commits(folder, initial, final, time)
                first_commit = gitRepo.get_creation_commit_module(module)
                gitRepo.checkout_commit(commits[-1])
                valid_platforms, _ = valid_platforms_versions(gitRepo.repo_dir)
                if platform and platform not in valid_platforms:
                    raise ValueError(f"Invalid platform: {platform}")
                elif commits == [''] and type == "integration" and module_exists(gitRepo.repo_dir, module):
                    raise ValueError(f"No changes found: {module}")
                elif commits == [''] and type == "integration" and not module_exists(gitRepo.repo_dir, module):
                    raise ValueError(f"Integration {module} not found in latest commit, is the name correct?")
                elif (
                    type == 'dependency'
                    and platform
                    and module not in get_dependency_list(gitRepo.repo_dir, [platform])
                ):
                    raise ValueError(
                        f"Dependency {module} not found in latest commit for the platform {platform}, "
                        "is the name correct?"
                    )
                elif (
                    type == 'dependency'
                    and not platform
                    and module not in get_dependency_list(gitRepo.repo_dir, valid_platforms)
                ):
                    raise ValueError(f"Dependency {module} not found in latest commit, is the name correct?")
                elif type == 'dependency' and commits == ['']:
                    raise ValueError(f"No changes found: {module}")
                if type == "dependency" and platform is None:
                    progress.remove_task(task)
                    for i, plat in enumerate(valid_platforms):
                        timeline_mode(
                            app, gitRepo, type, module, commits, threshold, plat, compressed, csv, i, None, progress
                        )
                else:
                    progress.remove_task(task)

                    timeline_mode(
                        app,
                        gitRepo,
                        type,
                        module,
                        commits,
                        threshold,
                        platform,
                        compressed,
                        csv,
                        None,
                        first_commit,
                        progress,
                    )

            except Exception as e:
                progress.remove_task(task)
                app.abort(str(e))


def timeline_mode(
    app: Application,
    gitRepo: GitRepo,
    type: str,
    module: str,
    commits: List[str],
    threshold: Optional[str],
    platform: Optional[str],
    compressed: bool,
    csv: bool,
    i: Optional[int],
    first_commit: Optional[str],
    progress: Progress,
) -> None:
    modules = get_repo_info(gitRepo, type, platform, module, commits, compressed, first_commit, progress)
    if modules != []:
        grouped_modules = group_modules(modules, platform, i)
        trimmed_modules = trim_modules(grouped_modules, threshold)
        if csv:
            print_csv(app, i, trimmed_modules)
        else:
            print_table(app, "Timeline for " + module, trimmed_modules)


def get_repo_info(
    gitRepo: GitRepo,
    type: str,
    platform: Optional[str],
    module: str,
    commits: List[str],
    compressed: bool,
    first_commit: Optional[str],
    progress: Progress,
) -> List[Dict[str, Union[str, int, date]]]:
    with progress:
        if type == "integration":
            file_data = process_commits(commits, module, gitRepo, progress, platform, type, compressed, first_commit)
        else:
            file_data = process_commits(commits, module, gitRepo, progress, platform, type, compressed, None)
    return file_data


def process_commits(
    commits: List[str],
    module: str,
    gitRepo: GitRepo,
    progress: Progress,
    platform: Optional[str],
    type: str,
    compressed: bool,
    first_commit: Optional[str],
) -> List[Dict[str, Union[str, int, date]]]:
    file_data = []
    task = progress.add_task("[cyan]Processing commits...", total=len(commits))
    repo = gitRepo.repo_dir

    folder = module if type == 'integration' else '.deps/resolved'
    for commit in commits:
        gitRepo.sparse_checkout_commit(commit, folder)
        date, author, message = gitRepo.get_commit_metadata(commit)
        date, message, commit = format_commit_data(date, message, commit, first_commit)
        if type == 'dependency' and date < MINIMUM_DATE:
            continue
        elif type == 'dependency':
            result = get_dependencies(repo, module, platform, commit, date, author, message, compressed)
            if result:
                file_data.append(result)
        elif type == 'integration':
            file_data = get_files(repo, module, commit, date, author, message, file_data, compressed)
        progress.advance(task)
    progress.remove_task(task)

    return file_data


def get_files(
    repo_path: str,
    module: str,
    commit: str,
    date: date,
    author: str,
    message: str,
    file_data: List[Dict[str, Union[str, int, date]]],
    compressed: bool,
) -> List[Dict[str, Union[str, int, date]]]:
    if not module_exists(repo_path, module):
        file_data.append(
            {
                "Size (Bytes)": 0,
                "Date": date,
                "Author": author,
                "Commit Message": "(DELETED) " + message,
                "Commit SHA": commit,
            }
        )
        return file_data

    ignored_files = {"datadog_checks_dev", "datadog_checks_tests_helper"}

    git_ignore = get_gitignore_files(repo_path)
    included_folder = "datadog_checks/"
    for root, _, files in os.walk(repo_path):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, repo_path)

            if is_valid_integration(relative_path, included_folder, ignored_files, git_ignore):
                size = compress(file_path) if compressed else os.path.getsize(file_path)
                file_data.append(
                    {
                        "Size (Bytes)": size,
                        "Date": date,
                        "Author": author,
                        "Commit Message": message,
                        "Commit SHA": commit,
                    }
                )
    return file_data


def get_dependencies(
    repo_path: str,
    module: str,
    platform: Optional[str],
    commit: str,
    date: date,
    author: str,
    message: str,
    compressed: bool,
) -> Optional[Dict[str, Union[str, int, date]]]:
    resolved_path = os.path.join(repo_path, ".deps/resolved")
    paths = os.listdir(resolved_path)
    version = get_version(paths, platform)
    for filename in paths:
        file_path = os.path.join(resolved_path, filename)
        if os.path.isfile(file_path) and is_correct_dependency(platform, version, filename):
            download_url = get_dependency(file_path, module)
            return (
                get_dependency_size(download_url, commit, date, author, message, compressed) if download_url else None
            )


def get_dependency(file_path: str, module: str) -> Optional[str]:
    with open(file_path, "r", encoding="utf-8") as file:
        file_content = file.read()
        for line in file_content.splitlines():
            match = re.search(r"([\w\-\d\.]+) @ (https?://[^\s#]+)", line)
            if not match:
                raise WrongDependencyFormat("The dependency format 'name @ link' is no longer supported.")
            name, url = match.groups()
            if name == module:
                return url
    return None


def get_dependency_size(
    download_url: str, commit: str, date: date, author: str, message: str, compressed: bool
) -> Dict[str, Union[str, int, date]]:
    if compressed:
        response = requests.head(download_url)
        response.raise_for_status()
        size = int(response.headers.get("Content-Length"))
    else:
        with requests.get(download_url, stream=True) as response:
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

    return {"Size (Bytes)": size, "Date": date, "Author": author, "Commit Message": message, "Commit SHA": commit}


def get_version(files: List[str], platform: Optional[str]) -> str:
    final_version = ''
    for file in files:
        if platform in file:
            version = file.split('_')[-1]
            match = re.search(r"\d+(?:\.\d+)?", version)
            version = match.group(0) if match else None
            if version > final_version:
                final_version = version
    return final_version if len(final_version) != 1 else 'py' + final_version


def group_modules(
    modules: List[Dict[str, Union[str, int, date]]], platform: Optional[str], i: Optional[int]
) -> List[Dict[str, Union[str, int, date]]]:
    grouped_aux = {}

    for file in modules:
        key = (file['Date'], file['Author'], file['Commit Message'], file['Commit SHA'])
        grouped_aux[key] = grouped_aux.get(key, 0) + file["Size (Bytes)"]
    if i is None:
        return [
            {
                "Commit SHA": commit,
                "Size (Bytes)": size,
                'Size': convert_size(size),
                'Delta (Bytes)': 'N/A',
                'Delta': 'N/A',
                "Date": date,
                "Author": author,
                "Commit Message": message,
            }
            for (date, author, message, commit), size in grouped_aux.items()
        ]
    else:
        return [
            {
                "Commit SHA": commit,
                "Size (Bytes)": size,
                'Size': convert_size(size),
                'Delta (Bytes)': 'N/A',
                'Delta': 'N/A',
                "Date": date,
                "Author": author,
                "Commit Message": message,
                'Platform': platform,
            }
            for (date, author, message, commit), size in grouped_aux.items()
        ]


def trim_modules(
    modules: List[Dict[str, Union[str, int, date]]], threshold: Optional[str] = None
) -> List[Dict[str, Union[str, int, date]]]:
    modules[0]['Delta (Bytes)'] = 0
    modules[0]['Delta'] = ' '
    trimmed_modules = [modules[0]]
    threshold_value = int(threshold) if threshold else 0

    for i in range(1, len(modules)):
        prev = modules[i - 1]
        curr = modules[i]
        delta = curr['Size (Bytes)'] - prev['Size (Bytes)']
        if abs(delta) > threshold_value or i == len(modules) - 1:
            curr['Delta (Bytes)'] = delta
            curr['Delta'] = convert_size(delta)
            trimmed_modules.append(curr)

    return trimmed_modules


def format_commit_data(date_str: str, message: str, commit: str, first_commit: Optional[str]) -> Tuple[date, str, str]:
    if commit == first_commit:
        message = "(NEW) " + message
    message = message if len(message) <= 35 else message[:30].rsplit(" ", 1)[0] + "..." + message.split()[-1]
    date = datetime.strptime(date_str, "%b %d %Y").date()
    return date, message, commit[:7]


def module_exists(path: str, module: str) -> bool:
    return os.path.exists(os.path.join(path, module))


def get_dependency_list(path: str, platforms: List[str]) -> Set[str]:
    resolved_path = os.path.join(path, ".deps/resolved")
    all_files = os.listdir(resolved_path)
    dependencies = set()

    for platform in platforms:
        version = get_version(all_files, platform)
        for filename in all_files:
            file_path = os.path.join(resolved_path, filename)
            if os.path.isfile(file_path) and is_correct_dependency(platform, version, filename):
                with open(file_path, "r", encoding="utf-8") as file:
                    matches = re.findall(r"([\w\-\d\.]+) @ https?://[^\s#]+", file.read())
                    dependencies.update(matches)
    return dependencies
