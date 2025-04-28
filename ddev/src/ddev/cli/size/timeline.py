import os
import re
import tempfile
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Set, Tuple

import click
import matplotlib.pyplot as plt
import requests
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from ddev.cli.application import Application

from .common import (
    CommitEntry,
    CommitEntryPlatformWithDelta,
    CommitEntryWithDelta,
    GitRepo,
    WrongDependencyFormat,
    compress,
    convert_size,
    extract_version_from_about_py,
    get_gitignore_files,
    is_correct_dependency,
    is_valid_integration,
    print_csv,
    print_table,
    valid_platforms_versions,
)

DEPENDENCY_FILE_CHANGE = datetime.strptime("Sep 17 2024", "%b %d %Y").date()
MINIMUM_DATE_DEPENDENCIES = datetime.strptime("Apr 3 2024", "%b %d %Y").date()
MINIMUM_DATE_INTEGRATIONS = datetime.strptime("Feb 1 2024", "%b %d %Y").date()
console = Console()


@click.command()
@click.argument("type", type=click.Choice(["integration", "dependency"]))
@click.argument("name")
@click.argument("initial_commit", required=False)
@click.argument("final_commit", required=False)
@click.option(
    "--time",
    help="Filter commits starting from a specific date. Accepts both absolute and relative formats, "
    "such as '2025-03-01', '2 weeks ago', or 'yesterday'",
)
@click.option(
    "--threshold",
    type=click.IntRange(min=0),
    help="Only show modules with size differences greater than a threshold in bytes",
)
@click.option(
    "--platform",
    help="Target platform to analyze. Only required for dependencies. If not specified, all platforms will be analyzed",
)
@click.option("--compressed", is_flag=True, help="Measure compressed size")
@click.option("--csv", is_flag=True, help="Output results in CSV format")
@click.option("--save_to_png_path", help="Path to save the treemap as PNG")
@click.option(
    "--show_gui",
    is_flag=True,
    help="Display a pop-up window with a line chart showing the size evolution of the selected module over time.",
)
@click.pass_obj
def timeline(
    app: Application,
    type: str,
    name: str,
    initial_commit: Optional[str],
    final_commit: Optional[str],
    time: Optional[str],
    threshold: Optional[int],
    platform: Optional[str],
    compressed: bool,
    csv: bool,
    save_to_png_path: str,
    show_gui: bool,
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
        if initial_commit and final_commit and len(initial_commit) < 7 and len(final_commit) < 7:
            raise click.BadParameter("Commit hashes must be at least 7 characters long")
        elif initial_commit and len(initial_commit) < 7:
            raise click.BadParameter("Initial commit hash must be at least 7 characters long.", param_hint="initial")
        elif final_commit and len(final_commit) < 7:
            raise click.BadParameter("Final commit hash must be at least 7 characters long.", param_hint="final")
        elif final_commit and initial_commit and final_commit == initial_commit:
            raise click.BadParameter("Commit hashes must be different")
        task = progress.add_task("[cyan]Calculating timeline...", total=None)
        url = app.repo.path
        with GitRepo(url) as gitRepo:
            try:
                folder = module if type == "integration" else ".deps/resolved"
                commits = gitRepo.get_module_commits(folder, initial_commit, final_commit, time)
                first_commit = gitRepo.get_creation_commit_module(module)
                gitRepo.checkout_commit(commits[-1])
                date_str, _, _ = gitRepo.get_commit_metadata(commits[-1])
                date = datetime.strptime(date_str, "%b %d %Y").date()
                if final_commit and (
                    (type == "integration" and date < MINIMUM_DATE_INTEGRATIONS)
                    or (type == "dependency" and date < MINIMUM_DATE_DEPENDENCIES)
                ):
                    raise ValueError(
                        f"Final commit must be after {MINIMUM_DATE_INTEGRATIONS.strftime('%b %d %Y')} "
                        "in case of Integrations "
                        f"and after {MINIMUM_DATE_DEPENDENCIES.strftime('%b %d %Y')} in case of Dependencies"
                    )
                valid_platforms, _ = valid_platforms_versions(gitRepo.repo_dir)
                if platform and platform not in valid_platforms:
                    raise ValueError(f"Invalid platform: {platform}")
                elif commits == [""] and type == "integration" and module_exists(gitRepo.repo_dir, module):
                    raise ValueError(f"No changes found for {type}: {module}")
                elif commits == [""] and type == "integration" and not module_exists(gitRepo.repo_dir, module):
                    raise ValueError(f"Integration {module} not found in latest commit, is the name correct?")
                elif (
                    type == "dependency"
                    and platform
                    and module not in get_dependency_list(gitRepo.repo_dir, {platform})
                ):
                    raise ValueError(
                        f"Dependency {module} not found in latest commit for the platform {platform}, "
                        "is the name correct?"
                    )
                elif (
                    type == "dependency"
                    and not platform
                    and module not in get_dependency_list(gitRepo.repo_dir, valid_platforms)
                ):
                    raise ValueError(f"Dependency {module} not found in latest commit, is the name correct?")
                elif type == "dependency" and commits == [""]:
                    raise ValueError(f"No changes found for {type}: {module}")
                if type == "dependency" and platform is None:
                    progress.remove_task(task)
                    for i, plat in enumerate(valid_platforms):
                        path = save_to_png_path
                        if save_to_png_path:
                            base, ext = os.path.splitext(save_to_png_path)
                            path = f"{base}_{plat}{ext}"
                        timeline_mode(
                            app,
                            gitRepo,
                            type,
                            module,
                            commits,
                            threshold,
                            plat,
                            compressed,
                            csv,
                            i,
                            None,
                            progress,
                            path,
                            show_gui,
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
                        save_to_png_path,
                        show_gui,
                    )

            except Exception as e:
                progress.stop()

                app.abort(str(e))


def timeline_mode(
    app: Application,
    gitRepo: GitRepo,
    type: str,
    module: str,
    commits: List[str],
    threshold: Optional[int],
    platform: Optional[str],
    compressed: bool,
    csv: bool,
    i: Optional[int],
    first_commit: Optional[str],
    progress: Progress,
    save_to_png_path: str,
    show_gui: bool,
) -> None:
    modules = get_repo_info(gitRepo, type, platform, module, commits, compressed, first_commit, progress)
    if modules != []:
        trimmed_modules = trim_modules(modules, threshold)
        grouped_modules = group_modules(trimmed_modules, platform, i)
        if csv:
            print_csv(app, i, grouped_modules)
        else:
            print_table(app, "Timeline for " + module, grouped_modules)
        if show_gui or save_to_png_path:
            plot_linegraph(grouped_modules, module, platform, show_gui, save_to_png_path)


def get_repo_info(
    gitRepo: GitRepo,
    type: str,
    platform: Optional[str],
    module: str,
    commits: List[str],
    compressed: bool,
    first_commit: Optional[str],
    progress: Progress,
) -> List[CommitEntry]:
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
) -> List[CommitEntry]:
    file_data: List[CommitEntry] = []
    task = progress.add_task("[cyan]Processing commits...", total=len(commits))
    repo = gitRepo.repo_dir

    folder = module if type == "integration" else ".deps/resolved"
    for commit in commits:
        gitRepo.sparse_checkout_commit(commit, folder)
        date_str, author, message = gitRepo.get_commit_metadata(commit)
        date, message, commit = format_commit_data(date_str, message, commit, first_commit)
        if type == "dependency" and date > MINIMUM_DATE_DEPENDENCIES:
            assert platform is not None
            result = get_dependencies(repo, module, platform, commit, date, author, message, compressed)
            if result:
                file_data.append(result)
        elif type == "integration":
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
    file_data: List[CommitEntry],
    compressed: bool,
) -> List[CommitEntry]:
    module_path = os.path.join(repo_path, module)

    if not module_exists(repo_path, module):
        file_data.append(
            {
                "Size_Bytes": 0,
                "Version": "",
                "Date": date,
                "Author": author,
                "Commit_Message": f"(DELETED) {message}",
                "Commit_SHA": commit,
            }
        )
        return file_data

    ignored_files = {"datadog_checks_dev", "datadog_checks_tests_helper"}
    git_ignore = get_gitignore_files(repo_path)
    included_folder = "datadog_checks/"

    total_size = 0
    version = ""

    for root, _, files in os.walk(module_path):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, repo_path)

            if not is_valid_integration(relative_path, included_folder, ignored_files, git_ignore):
                continue

            if file == "__about__.py" and "datadog_checks" in relative_path:
                version = extract_version_from_about_py(file_path)

            size = compress(file_path) if compressed else os.path.getsize(file_path)
            total_size += size

    file_data.append(
        {
            "Size_Bytes": total_size,
            "Version": version,
            "Date": date,
            "Author": author,
            "Commit_Message": message,
            "Commit_SHA": commit,
        }
    )
    return file_data


def get_dependencies(
    repo_path: str,
    module: str,
    platform: str,
    commit: str,
    date: date,
    author: str,
    message: str,
    compressed: bool,
) -> Optional[CommitEntry]:
    resolved_path = os.path.join(repo_path, ".deps/resolved")
    paths = os.listdir(resolved_path)
    version = get_version(paths, platform)
    for filename in paths:
        file_path = os.path.join(resolved_path, filename)
        if os.path.isfile(file_path) and is_correct_dependency(platform, version, filename):
            download_url, dep_version = get_dependency(file_path, module)
            return (
                get_dependency_size(download_url, dep_version, commit, date, author, message, compressed)
                if download_url and dep_version is not None
                else None
            )
    return None


def get_dependency(file_path: str, module: str) -> Tuple[Optional[str], Optional[str]]:
    with open(file_path, "r", encoding="utf-8") as file:
        file_content = file.read()
        for line in file_content.splitlines():
            match = re.search(r"([\w\-\d\.]+) @ (https?://[^\s#]+)", line)
            if not match:
                raise WrongDependencyFormat("The dependency format 'name @ link' is no longer supported.")
            name, url = match.groups()
            if name == module:
                version_match = re.search(rf"{re.escape(name)}-([0-9]+(?:\.[0-9]+)*)-", url)
                version = version_match.group(1) if version_match else ""
                return url, version
    return None, None


def get_dependency_size(
    download_url: str, version: str, commit: str, date: date, author: str, message: str, compressed: bool
) -> CommitEntry:
    if compressed:
        response = requests.head(download_url)
        response.raise_for_status()
        size_str = response.headers.get("Content-Length")
        if size_str is None:
            raise ValueError(f"Missing size for commit {commit}")
        size = int(size_str)
    else:
        with requests.get(download_url, stream=True) as response:
            response.raise_for_status()
            wheel_data = response.content

        with tempfile.TemporaryDirectory() as tmpdir:
            wheel_path = Path(tmpdir) / "package.whl"
            with open(wheel_path, "wb") as f:
                f.write(wheel_data)
            extract_path = Path(tmpdir) / "extracted"
            with zipfile.ZipFile(wheel_path, "r") as zip_ref:
                zip_ref.extractall(extract_path)

            size = 0
            for dirpath, _, filenames in os.walk(extract_path):
                for name in filenames:
                    file_path = os.path.join(dirpath, name)
                    size += os.path.getsize(file_path)

    commit_entry: CommitEntry = {
        "Size_Bytes": size,
        "Version": version,
        "Date": date,
        "Author": author,
        "Commit_Message": message,
        "Commit_SHA": commit,
    }
    return commit_entry


def get_version(files: List[str], platform: str) -> str:
    final_version = ""
    for file in files:
        if platform in file:
            curr_version = file.split("_")[-1]
            match = re.search(r"\d+(?:\.\d+)?", curr_version)
            version = match.group(0) if match else None
            if version and version > final_version:
                final_version = version
    return final_version if len(final_version) != 1 else "py" + final_version


def group_modules(
    modules: List[CommitEntryWithDelta], platform: Optional[str], i: Optional[int]
) -> List[CommitEntryWithDelta] | List[CommitEntryPlatformWithDelta]:
    if i is not None and platform:
        new_modules: List[CommitEntryPlatformWithDelta] = [{**entry, "Platform": platform} for entry in modules]
        return new_modules
    else:
        return modules


def trim_modules(
    modules: List[CommitEntry],
    threshold: Optional[int] = None,
) -> List[CommitEntryWithDelta]:
    threshold = threshold or 0

    trimmed_modules: List[CommitEntryWithDelta] = []

    first: CommitEntryWithDelta = {
        **modules[0],
        "Delta_Bytes": 0,
        "Delta": " ",
    }
    trimmed_modules.append(first)

    last_version = modules[0]["Version"]

    for j in range(1, len(modules)):
        prev = modules[j - 1]
        curr = modules[j]
        delta = curr["Size_Bytes"] - prev["Size_Bytes"]

        if abs(delta) > threshold or j == len(modules) - 1:
            new_entry: CommitEntryWithDelta = {
                **curr,
                "Delta_Bytes": delta,
                "Delta": convert_size(delta),
            }

            curr_version = curr["Version"]
            if curr_version != "" and curr_version != last_version:
                new_entry["Version"] = f"{last_version} -> {curr_version}"
                last_version = curr_version

            trimmed_modules.append(new_entry)

    return trimmed_modules


def format_commit_data(date_str: str, message: str, commit: str, first_commit: Optional[str]) -> Tuple[date, str, str]:
    if commit == first_commit:
        message = "(NEW) " + message
    message = message if len(message) <= 35 else message[:30].rsplit(" ", 1)[0] + "..." + message.split()[-1]
    date = datetime.strptime(date_str, "%b %d %Y").date()
    return date, message, commit[:7]


def module_exists(path: str, module: str) -> bool:
    return os.path.exists(os.path.join(path, module))


def get_dependency_list(path: str, platforms: Set[str]) -> Set[str]:
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


def plot_linegraph(
    modules: List[CommitEntryWithDelta] | List[CommitEntryPlatformWithDelta],
    module: str,
    platform: Optional[str],
    show: bool,
    path: Optional[str],
) -> None:
    dates = [entry["Date"] for entry in modules]
    sizes = [entry["Size_Bytes"] for entry in modules]
    title = f"Disk Usage Evolution of {module} for {platform}" if platform else f"Disk Usage Evolution of {module}"

    plt.figure(figsize=(10, 6))
    plt.plot(dates, sizes, linestyle="-")
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Size_Bytes")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    if path:
        plt.savefig(path)
    if show:
        plt.show()
    plt.close()
