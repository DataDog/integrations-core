import os
import re
import tempfile
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Literal, Optional, overload

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
    ParametersTimelineDependency,
    ParametersTimelineIntegration,
    WrongDependencyFormat,
    compress,
    convert_to_human_readable_size,
    extract_version_from_about_py,
    get_gitignore_files,
    get_valid_platforms,
    is_correct_dependency,
    is_valid_integration,
    print_csv,
    print_json,
    print_markdown,
    print_table,
)

MINIMUM_DATE_DEPENDENCIES = datetime.strptime(
    "Apr 3 2024", "%b %d %Y"
).date()  # Dependencies not available before this date due to a storage change
MINIMUM_LENGTH_COMMIT = 7
console = Console(stderr=True)


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
@click.option("--markdown", is_flag=True, help="Output in Markdown format")
@click.option("--json", is_flag=True, help="Output in JSON format")
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
    markdown: bool,
    json: bool,
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
        console=console,
    ) as progress:
        module = name  # module is the name of the integration or the dependency
        if sum([csv, markdown, json]) > 1:
            raise click.BadParameter("Only one output format can be selected: --csv, --markdown, or --json")
        elif (
            initial_commit
            and final_commit
            and len(initial_commit) < MINIMUM_LENGTH_COMMIT
            and len(final_commit) < MINIMUM_LENGTH_COMMIT
        ):
            raise click.BadParameter(f"Commit hashes must be at least {MINIMUM_LENGTH_COMMIT} characters long")
        elif initial_commit and len(initial_commit) < MINIMUM_LENGTH_COMMIT:
            raise click.BadParameter(
                f"Initial commit hash must be at least {MINIMUM_LENGTH_COMMIT} characters long.", param_hint="initial"
            )
        elif final_commit and len(final_commit) < MINIMUM_LENGTH_COMMIT:
            raise click.BadParameter(
                f"Final commit hash must be at least {MINIMUM_LENGTH_COMMIT} characters long.", param_hint="final"
            )
        elif final_commit and initial_commit and final_commit == initial_commit:
            raise click.BadParameter("Commit hashes must be different")
        task = progress.add_task("[cyan]Calculating timeline...", total=None)
        url = app.repo.path

        with GitRepo(url) as gitRepo:
            try:
                if final_commit and type == "dependency":
                    date_str, _, _ = gitRepo.get_commit_metadata(final_commit)
                    date = datetime.strptime(date_str, "%b %d %Y").date()
                    if date < MINIMUM_DATE_DEPENDENCIES:
                        raise ValueError(
                            f"Final commit must be after {MINIMUM_DATE_DEPENDENCIES.strftime('%b %d %Y')}"
                            " in case of Dependencies"
                        )
                folder = module if type == "integration" else ".deps/resolved"
                commits = gitRepo.get_module_commits(folder, initial_commit, final_commit, time)
                first_commit = gitRepo.get_creation_commit_module(module)
                if final_commit and commits == []:
                    gitRepo.checkout_commit(final_commit)
                elif commits != []:
                    gitRepo.checkout_commit(commits[-1])
                if type == "dependency":
                    valid_platforms = get_valid_platforms(gitRepo.repo_dir)
                    if platform and platform not in valid_platforms:
                        raise ValueError(f"Invalid platform: {platform}")
                if commits == [""] and type == "integration" and module_exists(gitRepo.repo_dir, module):
                    progress.remove_task(task)
                    progress.stop()
                    app.display_error(f"No changes found for {type}: {module}")
                    return
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
                    progress.remove_task(task)
                    progress.stop()
                    app.display_error(f"No changes found for {type}: {module}")
                    return
                if type == "dependency":
                    modules_plat: list[CommitEntryPlatformWithDelta] = []
                    multiple_plats_and_vers: Literal[True] = True
                    progress.remove_task(task)
                    dep_parameters: ParametersTimelineDependency
                    if not platform:
                        for plat in valid_platforms:
                            path = None
                            if save_to_png_path:
                                base, ext = os.path.splitext(save_to_png_path)
                                path = f"{base}_{plat}{ext}"
                            dep_parameters = {
                                "app": app,
                                "type": "dependency",
                                "module": module,
                                "threshold": threshold,
                                "platform": plat,
                                "compressed": compressed,
                                "csv": csv,
                                "markdown": markdown,
                                "json": json,
                                "save_to_png_path": path,
                                "show_gui": show_gui,
                                "first_commit": None,
                            }

                            modules_plat.extend(
                                timeline_mode(
                                    gitRepo,
                                    commits,
                                    dep_parameters,
                                    multiple_plats_and_vers,
                                    progress,
                                )
                            )

                    else:
                        dep_parameters = {
                            "app": app,
                            "type": "dependency",
                            "module": module,
                            "threshold": threshold,
                            "platform": platform,
                            "compressed": compressed,
                            "csv": csv,
                            "markdown": markdown,
                            "json": json,
                            "save_to_png_path": save_to_png_path,
                            "show_gui": show_gui,
                            "first_commit": None,
                        }
                        modules_plat.extend(
                            timeline_mode(
                                gitRepo,
                                commits,
                                dep_parameters,
                                multiple_plats_and_vers,
                                progress,
                            )
                        )

                    if csv:
                        print_csv(app, modules_plat)
                    elif json:
                        print_json(app, modules_plat)
                else:
                    modules: list[CommitEntryWithDelta] = []
                    multiple_plat_and_ver: Literal[False] = False
                    int_parameters: ParametersTimelineIntegration = {
                        "app": app,
                        "type": "integration",
                        "module": module,
                        "threshold": threshold,
                        "platform": None,
                        "compressed": compressed,
                        "csv": csv,
                        "markdown": markdown,
                        "json": json,
                        "save_to_png_path": save_to_png_path,
                        "show_gui": show_gui,
                        "first_commit": first_commit,
                    }
                    progress.remove_task(task)
                    modules.extend(
                        timeline_mode(
                            gitRepo,
                            commits,
                            int_parameters,
                            multiple_plat_and_ver,
                            progress,
                        )
                    )
                    if csv:
                        print_csv(app, modules)
                    elif json:
                        print_json(app, modules)

            except Exception as e:
                progress.stop()
                app.abort(str(e))


@overload
def timeline_mode(
    gitRepo: GitRepo,
    commits: list[str],
    params: ParametersTimelineDependency,
    multiple_plats_and_vers: Literal[True],
    progress: Progress,
) -> list[CommitEntryPlatformWithDelta]: ...


@overload
def timeline_mode(
    gitRepo: GitRepo,
    commits: list[str],
    params: ParametersTimelineIntegration,
    multiple_plats_and_vers: Literal[False],
    progress: Progress,
) -> list[CommitEntryWithDelta]: ...


@overload
def timeline_mode(
    gitRepo: GitRepo,
    commits: list[str],
    params: ParametersTimelineDependency,
    multiple_plats_and_vers: Literal[False],
    progress: Progress,
) -> list[CommitEntryWithDelta]: ...


def timeline_mode(
    gitRepo: GitRepo,
    commits: list[str],
    params: ParametersTimelineIntegration | ParametersTimelineDependency,
    multiple_plats_and_vers: bool,
    progress: Progress,
) -> list[CommitEntryWithDelta] | list[CommitEntryPlatformWithDelta]:
    if params["type"] == "integration":
        modules = get_repo_info(
            gitRepo,
            params,
            commits,
            progress,
        )
    else:
        modules = get_repo_info(
            gitRepo,
            params,
            commits,
            progress,
        )
    trimmed_modules = trim_modules(modules, params["threshold"])
    formatted_modules = format_modules(trimmed_modules, params["platform"], multiple_plats_and_vers)

    if params["markdown"]:
        print_markdown(params["app"], "Timeline for " + params["module"], formatted_modules)
    elif not params["csv"] and not params["json"]:
        print_table(params["app"], "Timeline for " + params["module"], formatted_modules)

    if params["show_gui"] or params["save_to_png_path"]:
        plot_linegraph(
            formatted_modules, params["module"], params["platform"], params["show_gui"], params["save_to_png_path"]
        )

    return formatted_modules


@overload
def get_repo_info(
    gitRepo: GitRepo,
    params: ParametersTimelineIntegration,
    commits: list[str],
    progress: Progress,
) -> list[CommitEntry]: ...


@overload
def get_repo_info(
    gitRepo: GitRepo,
    params: ParametersTimelineDependency,
    commits: list[str],
    progress: Progress,
) -> list[CommitEntry]: ...


def get_repo_info(
    gitRepo: GitRepo,
    params: ParametersTimelineIntegration | ParametersTimelineDependency,
    commits: list[str],
    progress: Progress,
) -> list[CommitEntry]:
    """
    Retrieves size and metadata info for a module across multiple commits.

    Args:
        gitRepo: Active GitRepo instance.
        params: Parameters Typed Dictionary containing module name, type, platform, and other configuration options.
        commits: List of commits to process.
        first_commit: First commit hash where the given integration was introduced (only for integrations).
        progress: Progress bar instance.

    Returns:
        A list of CommitEntry objects with size, version, date, author, commit message and commit hash.
    """
    with progress:
        if params["type"] == "integration":
            file_data = process_commits(commits, params, gitRepo, progress, params["first_commit"])
        else:
            file_data = process_commits(commits, params, gitRepo, progress, params["first_commit"])
    return file_data


@overload
def process_commits(
    commits: list[str],
    params: ParametersTimelineIntegration,
    gitRepo: GitRepo,
    progress: Progress,
    first_commit: str,
) -> list[CommitEntry]: ...


@overload
def process_commits(
    commits: list[str],
    params: ParametersTimelineDependency,
    gitRepo: GitRepo,
    progress: Progress,
    first_commit: None,
) -> list[CommitEntry]: ...


def process_commits(
    commits: list[str],
    params: ParametersTimelineIntegration | ParametersTimelineDependency,
    gitRepo: GitRepo,
    progress: Progress,
    first_commit: Optional[str],
) -> list[CommitEntry]:
    """
    Processes a list of commits for a given integration or dependency.

    For each commit, it checks out the corresponding version of the module,
    retrieves its metadata, and calculates its size.

    Args:
        commits: List of commit SHAs to process.
        params: ParametersTimeline dict containing module name, type, platform, and other configuration options.
        gitRepo: GitRepo instance managing the repository.
        progress: Progress bar instance.
        first_commit: First commit hash where the given integration was introduced (only for integrations).

    Returns:
        A list of CommitEntry objects with commit metadata and size information.
    """
    file_data: list[CommitEntry] = []
    task = progress.add_task("[cyan]Processing commits...", total=len(commits))
    repo = gitRepo.repo_dir

    folder = params["module"] if params["type"] == "integration" else ".deps/resolved"

    for commit in commits:
        gitRepo.sparse_checkout_commit(commit, folder)
        date_str, author, message = gitRepo.get_commit_metadata(commit)
        date, message, commit = format_commit_data(date_str, message, commit, first_commit)
        if params["type"] == "dependency" and date > MINIMUM_DATE_DEPENDENCIES:
            assert params["platform"] is not None
            result = get_dependencies(
                repo,
                params["module"],
                params["platform"],
                commit,
                date,
                author,
                message,
                params["compressed"],
            )
            if result:
                file_data.append(result)
        elif params["type"] == "integration":
            file_data = get_files(
                repo,
                params["module"],
                commit,
                date,
                author,
                message,
                file_data,
                params["compressed"],
            )

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
    file_data: list[CommitEntry],
    compressed: bool,
) -> list[CommitEntry]:
    """
    Calculates integration file sizes and versions from a repository.

    If the integration folder no longer exists, a 'Deleted' entry is added. Otherwise,
    it walks the module directory, sums file sizes, extracts the version, and appends a CommitEntry.

    Args:
        repo_path: Path to the local Git repository.
        module: Name of the integration.
        commit: Commit SHA being analyzed.
        date: Commit date.
        author: Commit author.
        message: Commit message.
        file_data: List to append the result to.
        compressed: Whether to use compressed file sizes.

    Returns:
        The updated file_data list with one new CommitEntry appended.
    """
    module_path = os.path.join(repo_path, module)

    if not module_exists(repo_path, module):
        file_data.append(
            {
                "Size_Bytes": 0,
                "Version": "Deleted",
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
    """
    Returns the size and metadata of a dependency for a given commit and platform.

    Args:
        repo_path: Path to the repository.
        module: Dependency name to look for.
        platform: Target platform to match (e.g., 'linux-x86_64').
        commit: Commit SHA being analyzed.
        date: Commit date.
        author: Commit author.
        message: Commit message.
        compressed: Whether to calculate compressed size or uncompressed.

    Returns:
        A CommitEntry with size and metadata if the dependency is found, else None.
    """
    resolved_path = os.path.join(repo_path, ".deps/resolved")
    paths = os.listdir(resolved_path)
    version = get_version(paths, platform)
    for filename in paths:
        file_path = os.path.join(resolved_path, filename)
        if os.path.isfile(file_path) and is_correct_dependency(platform, version, filename):
            download_url, dep_version = get_dependency_data(file_path, module)
            return (
                get_dependency_size(download_url, dep_version, commit, date, author, message, compressed)
                if download_url and dep_version is not None
                else None
            )
    return None


def get_dependency_data(file_path: str, module: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parses a dependency file and extracts the dependency name, download URL, and version.

    Args:
        file_path: Path to the file containing the dependencies.
        module: Name of the dependency.

    Returns:
        A tuple of two strings:
            - Download URL
            - Extracted dependency version
    """
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
    """
    Calculates the size of a dependency wheel at a given commit.

    Args:
        download_url: URL to download the wheel file.
        version: Dependency version.
        commit: Commit SHA being analyzed.
        date: Commit date.
        author: Commit author.
        message: Commit message.
        compressed: If True, use Content-Length. If False, download and decompress to calculate size.

    Returns:
        A CommitEntry with size and metadata for the given dependency and commit.
    """
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


def get_version(files: list[str], platform: str) -> str:
    """
    Returns the latest Python version for the given target platform based on .deps/resolved filenames.

    Args:
        files: List of filenames from the .deps/resolved folder.
        platform: Target platform.

    Returns:
        If the version is a single digit (e.g., '3'), returns 'py3';
        otherwise (e.g., '3.12'), returns it as-is.
    """
    final_version = ""
    for file in files:
        if platform in file:
            curr_version = file.split("_")[-1]
            match = re.search(r"\d+(?:\.\d+)?", curr_version)
            version = match.group(0) if match else None
            if version and version > final_version:
                final_version = version
    return final_version if len(final_version) != 1 else "py" + final_version


def format_modules(
    modules: list[CommitEntryWithDelta],
    platform: Optional[str],
    multiple_plats_and_vers: bool,
) -> list[CommitEntryWithDelta] | list[CommitEntryPlatformWithDelta]:
    """
    Formats the modules list, adding platform and Python version information if needed.

    If the modules list is empty, returns a default empty entry (with or without platform information).

    Args:
        modules: List of modules to format.
        platform: Platform string to add to each entry if needed.
        version: Python version string to add to each entry if needed.
        i: Index of the current platform, version) combination being processed.
           If None, it means the data is being processed for only one platform.

    Returns:
        A list of formatted entries.
    """
    if modules == [] and multiple_plats_and_vers and platform:
        empty_module_platform: CommitEntryPlatformWithDelta = {
            "Size_Bytes": 0,
            "Version": "",
            "Date": datetime.min.date(),
            "Author": "",
            "Commit_Message": "",
            "Commit_SHA": "",
            "Delta_Bytes": 0,
            "Delta": " ",
            "Platform": "",
        }
        return [empty_module_platform]
    elif modules == []:
        empty_module: CommitEntryWithDelta = {
            "Size_Bytes": 0,
            "Version": "",
            "Date": datetime.min.date(),
            "Author": "",
            "Commit_Message": "",
            "Commit_SHA": "",
            "Delta_Bytes": 0,
            "Delta": " ",
        }
        return [empty_module]
    elif multiple_plats_and_vers and platform:
        new_modules: list[CommitEntryPlatformWithDelta] = [{**entry, "Platform": platform} for entry in modules]
        return new_modules
    else:
        return modules


def trim_modules(
    modules: list[CommitEntry],
    threshold: Optional[int] = None,
) -> list[CommitEntryWithDelta]:
    """
    Filters a list of commit entries, keeping only those with significant size changes.

    Args:
        modules: List of CommitEntry items ordered by commit date.
        threshold: Minimum size change (in bytes) required to keep an entry. Defaults to 0.

    Returns:
        A list of CommitEntryWithDelta objects:
            - Always includes the first and last entry.
            - Includes intermediate entries where size difference exceeds the threshold.
            - Adds Delta_Bytes and human-readable Delta for each included entry.
            - Marks version transitions as 'X -> Y' when the version changes.
    """
    if modules == []:
        empty_modules: list[CommitEntryWithDelta] = []
        return empty_modules

    threshold = threshold or 0

    trimmed_modules: list[CommitEntryWithDelta] = []

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
                "Delta": convert_to_human_readable_size(delta),
            }

            curr_version = curr["Version"]
            if curr_version != "" and curr_version != last_version:
                new_entry["Version"] = f"{last_version} -> {curr_version}"
                last_version = curr_version

            trimmed_modules.append(new_entry)

    return trimmed_modules


def format_commit_data(date_str: str, message: str, commit: str, first_commit: Optional[str]) -> tuple[date, str, str]:
    """
    Formats commit metadata by shortening the message, marking the first commit, and parsing the date.
    Args:
        date_str: Commit date as a string (e.g., 'Apr 3 2024').
        message: Original commit message.
        commit: commit SHA.
        first_commit: First commit hash where the given integration was introduced (only for integrations).

    Returns:
        A tuple containing:
            - Parsed date object,
            - Shortened and possibly annotated message,
            - Shortened commit SHA .
    """
    if commit == first_commit:
        message = "(NEW) " + message
    # Truncates the commit message if it's too long, keeping the first words and the PR number within the allowed length
    MAX_LENGTH_COMMIT = 45
    PR_NUMBER_LENGTH = 8
    message = (
        message
        if len(message) <= MAX_LENGTH_COMMIT
        else message[: MAX_LENGTH_COMMIT - PR_NUMBER_LENGTH - 3].rsplit(" ", 1)[0] + "..." + message.split()[-1]
    )
    date = datetime.strptime(date_str, "%b %d %Y").date()
    return date, message, commit[:MINIMUM_LENGTH_COMMIT]


def module_exists(path: str, module: str) -> bool:
    """
    Checks if the given module exists at the specified path
    """
    return os.path.exists(os.path.join(path, module))


def get_dependency_list(path: str, platforms: set[str]) -> set[str]:
    """
    Returns the set of dependencies from the .deps/resolved folder for the latest version of the given platform.
    """
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
    modules: list[CommitEntryWithDelta] | list[CommitEntryPlatformWithDelta],
    module: str,
    platform: Optional[str],
    show: bool,
    path: Optional[str],
) -> None:
    """
    Plots the disk usage evolution over time for a given module.

    Args:
        modules: List of commit entries with size and date information.
        module: Name of the module to display in the title.
        platform: Target platform (used in the title if provided).
        show: If True, displays the plot interactively.
        path: If provided, saves the plot to this file path.
    """
    if not any(str(value).strip() not in ("", "0", "0001-01-01") for value in modules[0].values()):  # table is empty
        return

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
