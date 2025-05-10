# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
import zlib
from datetime import date
from pathlib import Path
from types import TracebackType
from typing import Literal, Optional, Type, TypedDict

import matplotlib.cm as cm
import matplotlib.pyplot as plt
import requests
import squarify
from matplotlib.patches import Patch

from ddev.cli.application import Application


class FileDataEntry(TypedDict):
    Name: str  # Integration/Dependency name
    Version: str  # Version of the Integration/Dependency
    Size_Bytes: int  # Size in bytes
    Size: str  # Human-readable size
    Type: str  # Integration/Dependency


class FileDataEntryPlatformVersion(FileDataEntry):
    Platform: str  # Target platform (e.g. linux-aarch64)
    Python_Version: str  # Target Python version (e.g. 3.12)


class CommitEntry(TypedDict):
    Size_Bytes: int  # Total size in bytes at commit
    Version: str  # Version of the Integration/Dependency at commit
    Date: date  # Commit date
    Author: str  # Commit author
    Commit_Message: str  # Commit message
    Commit_SHA: str  # Commit SHA hash


class CommitEntryWithDelta(CommitEntry):
    Delta_Bytes: int  # Size change in bytes compared to previous commit
    Delta: str  # Human-readable size change


class CommitEntryPlatformWithDelta(CommitEntryWithDelta):
    Platform: str  # Target platform (e.g. linux-aarch64)


class Parameters(TypedDict):
    app: Application
    platform: str
    version: str
    compressed: bool
    csv: bool
    markdown: bool
    json: bool
    save_to_png_path: Optional[str]
    show_gui: bool


class ParametersTimeline(TypedDict):
    app: Application
    module: str
    threshold: Optional[int]
    compressed: bool
    csv: bool
    markdown: bool
    json: bool
    save_to_png_path: Optional[str]
    show_gui: bool


class ParametersTimelineIntegration(ParametersTimeline):
    type: Literal["integration"]
    first_commit: str
    platform: None


class ParametersTimelineDependency(ParametersTimeline):
    type: Literal["dependency"]
    first_commit: None
    platform: str


def get_valid_platforms(repo_path: Path | str) -> set[str]:
    """
    Extracts the platforms we support from the .deps/resolved file names.
    """
    resolved_path = os.path.join(repo_path, os.path.join(repo_path, ".deps", "resolved"))
    platforms = []
    for file in os.listdir(resolved_path):
        platforms.append("_".join(file.split("_")[:-1]))
    return set(platforms)


def get_valid_versions(repo_path: Path | str) -> set[str]:
    """
    Extracts the Python versions we support from the .deps/resolved file names.
    """
    resolved_path = os.path.join(repo_path, os.path.join(repo_path, ".deps", "resolved"))
    versions = []
    for file in os.listdir(resolved_path):
        match = re.search(r"\d+\.\d+", file)
        if match:
            versions.append(match.group())
    return set(versions)


def is_correct_dependency(platform: str, version: str, name: str) -> bool:
    return platform in name and version in name


def is_valid_integration(path: str, included_folder: str, ignored_files: set[str], git_ignore: list[str]) -> bool:
    # It is not an integration
    if path.startswith("."):
        return False
    # It is part of an integration and it is not in the datadog_checks folder
    elif included_folder not in path:
        return False
    # It is an irrelevant file
    elif any(ignore in path for ignore in ignored_files):
        return False
    # This file is contained in .gitignore
    elif any(ignore in path for ignore in git_ignore):
        return False
    else:
        return True


def get_gitignore_files(repo_path: str | Path) -> list[str]:
    gitignore_path = os.path.join(repo_path, ".gitignore")
    with open(gitignore_path, "r", encoding="utf-8") as file:
        gitignore_content = file.read()
        ignored_patterns = [
            line.strip() for line in gitignore_content.splitlines() if line.strip() and not line.startswith("#")
        ]
        return ignored_patterns


def convert_to_human_readable_size(size_bytes: float) -> str:
    for unit in [" B", " KB", " MB", " GB"]:
        if abs(size_bytes) < 1024:
            return str(round(size_bytes, 2)) + unit
        size_bytes /= 1024
    return str(round(size_bytes, 2)) + " TB"


def compress(file_path: str) -> int:
    compressor = zlib.compressobj()
    compressed_size = 0
    chunk_size = 8192
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            compressed_chunk = compressor.compress(chunk)
            compressed_size += len(compressed_chunk)
        compressed_size += len(compressor.flush())
    return compressed_size


def get_files(repo_path: str | Path, compressed: bool) -> list[FileDataEntry]:
    """
    Calculates integration file sizes and versions from a repository.
    """
    ignored_files = {"datadog_checks_dev", "datadog_checks_tests_helper"}
    git_ignore = get_gitignore_files(repo_path)
    included_folder = "datadog_checks/"

    integration_sizes: dict[str, int] = {}
    integration_versions: dict[str, str] = {}

    for root, _, files in os.walk(repo_path):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, repo_path)

            if not is_valid_integration(relative_path, included_folder, ignored_files, git_ignore):
                continue
            path = Path(relative_path)
            parts = path.parts

            integration_name = parts[0]

            size = compress(file_path) if compressed else os.path.getsize(file_path)
            integration_sizes[integration_name] = integration_sizes.get(integration_name, 0) + size

            if integration_name not in integration_versions and file == "__about__.py":
                version = extract_version_from_about_py(file_path)
                integration_versions[integration_name] = version

    return [
        {
            "Name": name,
            "Version": integration_versions.get(name, ""),
            "Size_Bytes": size,
            "Size": convert_to_human_readable_size(size),
            "Type": "Integration",
        }
        for name, size in integration_sizes.items()
    ]


def extract_version_from_about_py(path: str) -> str:
    """
    Extracts the __version__ string from a given __about__.py file.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("__version__"):
                    return line.split("=")[1].strip().strip("'\"")
    except Exception:
        pass
    return ""


def get_dependencies(repo_path: str | Path, platform: str, version: str, compressed: bool) -> list[FileDataEntry]:
    """
    Gets the list of dependencies for a given platform and Python version.
    Each FileDataEntry includes: Name, Version, Size_Bytes, Size, and Type.

    Args:
        repo_path: Path to the repository.
        platform: Target platform.
        version: Target Python version.
        compressed: If True, measure compressed file sizes. If False, measure uncompressed sizes.

    Returns:
        A list of FileDataEntry dictionaries containing the dependency information.
    """
    resolved_path = os.path.join(repo_path, os.path.join(repo_path, ".deps", "resolved"))

    for filename in os.listdir(resolved_path):
        file_path = os.path.join(resolved_path, filename)

        if os.path.isfile(file_path) and is_correct_dependency(platform, version, filename):
            deps, download_urls, versions = get_dependencies_list(file_path)
            return get_dependencies_sizes(deps, download_urls, versions, compressed)
    return []


def get_dependencies_list(file_path: str) -> tuple[list[str], list[str], list[str]]:
    """
    Parses a dependency file and extracts the dependency names, download URLs, and versions.
    """
    download_urls = []
    deps = []
    versions = []
    with open(file_path, "r", encoding="utf-8") as file:
        file_content = file.read()
        for line in file_content.splitlines():
            match = re.search(r"([\w\-\d\.]+) @ (https?://[^\s#]+)", line)
            if not match:
                raise WrongDependencyFormat("The dependency format 'name @ link' is no longer supported.")
            name = match.group(1)
            url = match.group(2)

            deps.append(name)
            download_urls.append(url)
            version_match = re.search(rf"{re.escape(name)}-([0-9]+(?:\.[0-9]+)*)-", url)
            if version_match:
                versions.append(version_match.group(1))

    return deps, download_urls, versions


def get_dependencies_sizes(
    deps: list[str], download_urls: list[str], versions: list[str], compressed: bool
) -> list[FileDataEntry]:
    """
    Calculates the sizes of dependencies, either compressed or uncompressed.

    Args:
        deps: List of dependency names.
        download_urls: Corresponding download URLs for the dependencies.
        versions: Corresponding version strings for the dependencies.
        compressed: If True, use the Content-Length from the HTTP headers.
                    If False, download, extract, and compute actual uncompressed size.
    """
    file_data: list[FileDataEntry] = []
    for dep, url, version in zip(deps, download_urls, versions, strict=False):
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
                with zipfile.ZipFile(wheel_path, "r") as zip_ref:
                    zip_ref.extractall(extract_path)

                size = 0
                for dirpath, _, filenames in os.walk(extract_path):
                    for name in filenames:
                        file_path = os.path.join(dirpath, name)
                        size += os.path.getsize(file_path)
        file_data.append(
            {
                "Name": str(dep),
                "Version": version,
                "Size_Bytes": int(size),
                "Size": convert_to_human_readable_size(size),
                "Type": "Dependency",
            }
        )

    return file_data


def format_modules(
    modules: list[FileDataEntry],
    platform: str,
    py_version: str,
    multiple_plats_and_vers: bool,
) -> list[FileDataEntryPlatformVersion] | list[FileDataEntry]:
    """
    Formats the modules list, adding platform and Python version information if needed.

    If the modules list is empty, returns a default empty entry (with or without platform information).

    Args:
        modules: List of modules to format.
        platform: Platform string to add to each entry if needed.
        version: Python version string to add to each entry if needed.
        i: Index of the current (platform, version) combination being processed.
           If None, it means the data is being processed for only one combination of platform and version.

    Returns:
        A list of formatted entries.
    """
    if modules == [] and not multiple_plats_and_vers:
        empty_entry: FileDataEntry = {
            "Name": "",
            "Version": "",
            "Size_Bytes": 0,
            "Size": "",
            "Type": "",
        }
        return [empty_entry]
    elif modules == []:
        empty_entry_with_platform: FileDataEntryPlatformVersion = {
            "Name": "",
            "Version": "",
            "Size_Bytes": 0,
            "Size": "",
            "Type": "",
            "Platform": "",
            "Python_Version": "",
        }
        return [empty_entry_with_platform]
    elif multiple_plats_and_vers:
        new_modules: list[FileDataEntryPlatformVersion] = [
            {**entry, "Platform": platform, "Python_Version": py_version} for entry in modules
        ]
        return new_modules
    else:
        return modules


def print_json(
    app: Application,
    modules: (
        list[FileDataEntry]
        | list[FileDataEntryPlatformVersion]
        | list[CommitEntryWithDelta]
        | list[CommitEntryPlatformWithDelta]
    ),
) -> None:
    printed_yet = False
    app.display("[")
    for row in modules:
        if any(str(value).strip() not in ("", "0", "0001-01-01") for value in row.values()):
            if printed_yet:
                app.display(",")
            app.display(json.dumps(row, default=str))
            printed_yet = True

    app.display("]")


def print_csv(
    app: Application,
    modules: (
        list[FileDataEntry]
        | list[FileDataEntryPlatformVersion]
        | list[CommitEntryWithDelta]
        | list[CommitEntryPlatformWithDelta]
    ),
) -> None:
    headers = [k for k in modules[0].keys() if k not in ["Size", "Delta"]]
    app.display(",".join(headers))

    for row in modules:
        if any(str(value).strip() not in ("", "0", "0001-01-01") for value in row.values()):
            app.display(",".join(format(str(row.get(h, ""))) for h in headers))


def format(s: str) -> str:
    """
    Wraps the string in double quotes if it contains a comma, for safe CSV formatting.
    """
    return f'"{s}"' if "," in s else s


def print_markdown(
    app: Application,
    title: str,
    modules: (
        list[FileDataEntry]
        | list[FileDataEntryPlatformVersion]
        | list[CommitEntryWithDelta]
        | list[CommitEntryPlatformWithDelta]
    ),
) -> None:
    if any(str(value).strip() not in ("", "0", "0001-01-01") for value in modules[0].values()):  # table is not empty
        headers = [k for k in modules[0].keys() if "Bytes" not in k]
        app.display_markdown(f"### {title}")
        app.display_markdown("| " + " | ".join(headers) + " |")
        app.display_markdown("| " + " | ".join("---" for _ in headers) + " |")

        for row in modules:
            app.display_markdown("| " + " | ".join(format(str(row.get(h, ""))) for h in headers) + " |")


def print_table(
    app: Application,
    mode: str,
    modules: (
        list[FileDataEntry]
        | list[FileDataEntryPlatformVersion]
        | list[CommitEntryWithDelta]
        | list[CommitEntryPlatformWithDelta]
    ),
) -> None:
    columns = [col for col in modules[0].keys() if "Bytes" not in col]
    modules_table: dict[str, dict[int, str]] = {col: {} for col in columns}
    for i, row in enumerate(modules):
        if any(str(value).strip() not in ("", "0", "0001-01-01") for value in row.values()):
            for key in columns:
                modules_table[key][i] = str(row.get(key, ""))

    app.display_table(mode, modules_table)


def plot_treemap(
    modules: list[FileDataEntry] | list[FileDataEntryPlatformVersion],
    title: str,
    show: bool,
    mode: Literal["status", "diff"] = "status",
    path: Optional[str] = None,
) -> None:
    if not any(str(value).strip() not in ("", "0") for value in modules[0].values()):
        # table is empty
        return

    # Initialize figure and axis
    plt.figure(figsize=(12, 8))
    ax = plt.gca()
    ax.set_axis_off()

    # Calculate the rectangles
    if mode == "status":
        rects, colors, legend_handles = plot_status_treemap(modules)

    if mode == "diff":
        rects, colors, legend_handles = plot_diff_treemap(modules)

    draw_treemap_rects_with_labels(ax, rects, modules, colors)

    # Finalize layout and show/save plot
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)

    plt.title(title, fontsize=16)

    plt.legend(handles=legend_handles, title="Type", loc="center left", bbox_to_anchor=(1.0, 0.5))
    plt.subplots_adjust(right=0.8)
    plt.tight_layout()

    if show:
        plt.show()
    if path:
        plt.savefig(path, bbox_inches="tight", format="png")


def plot_status_treemap(
    modules: list[FileDataEntry] | list[FileDataEntryPlatformVersion],
) -> tuple[list[dict[str, float]], list[tuple[float, float, float, float]], list[Patch]]:
    # Calculate the area of the rectangles
    sizes = [mod["Size_Bytes"] for mod in modules]
    norm_sizes = squarify.normalize_sizes(sizes, 100, 100)
    rects = squarify.squarify(norm_sizes, 0, 0, 100, 100)

    # Define the colors for each type
    cmap_int = cm.get_cmap("Purples")
    cmap_dep = cm.get_cmap("Reds")

    # Assign colors based on type and normalized size
    colors = []
    max_area = max(norm_sizes) or 1
    for mod, area in zip(modules, norm_sizes, strict=False):
        intensity = scale_colors_treemap(area, max_area)
        if mod["Type"] == "Integration":
            colors.append(cmap_int(intensity))
        elif mod["Type"] == "Dependency":
            colors.append(cmap_dep(intensity))
        else:
            colors.append("#999999")
    # Define the legend
    legend_handles = [
        Patch(color=cm.get_cmap("Purples")(0.6), label="Integration"),
        Patch(color=cm.get_cmap("Reds")(0.6), label="Dependency"),
    ]
    return rects, colors, legend_handles


def plot_diff_treemap(
    modules: list[FileDataEntry] | list[FileDataEntryPlatformVersion],
) -> tuple[list[dict[str, float]], list[tuple[float, float, float, float]], list[Patch]]:
    # Define the colors for each type
    cmap_pos = cm.get_cmap("Oranges")
    cmap_neg = cm.get_cmap("Blues")

    # Separate in negative and positive differences
    positives = [mod for mod in modules if mod["Size_Bytes"] > 0]
    negatives = [mod for mod in modules if mod["Size_Bytes"] < 0]

    sizes_pos = [mod["Size_Bytes"] for mod in positives]
    sizes_neg = [abs(mod["Size_Bytes"]) for mod in negatives]

    sum_pos = sum(sizes_pos)
    sum_neg = sum(sizes_neg)

    canvas_area = 50 * 100

    # Determine dominant side and scale layout accordingly
    if sum_pos >= sum_neg:
        norm_sizes_pos = [s / sum_pos * canvas_area for s in sizes_pos]
        norm_sizes_neg = [s / sum_pos * canvas_area for s in sizes_neg]
        rects_neg = squarify.squarify(norm_sizes_neg, 0, 0, 50, 100)
        rects_pos = squarify.squarify(norm_sizes_pos, 50, 0, 50, 100)

    else:
        norm_sizes_neg = [s / sum_neg * canvas_area for s in sizes_neg]
        norm_sizes_pos = [s / sum_neg * canvas_area for s in sizes_pos]
        rects_neg = squarify.squarify(norm_sizes_neg, 0, 0, 50, 100)
        rects_pos = squarify.squarify(norm_sizes_pos, 50, 0, 50, 100)

    # Merge layout and module lists
    rects = rects_neg + rects_pos
    modules = negatives + positives

    # Assign colors based on type and normalized size
    colors = []
    max_area = max(norm_sizes_pos + norm_sizes_neg) or 1

    for area in norm_sizes_neg:
        intensity = scale_colors_treemap(area, max_area)
        colors.append(cmap_neg(intensity))

    for area in norm_sizes_pos:
        intensity = scale_colors_treemap(area, max_area)
        colors.append(cmap_pos(intensity))

    legend_handles = [
        Patch(color=cm.get_cmap("Oranges")(0.7), label="Increase"),
        Patch(color=cm.get_cmap("Blues")(0.7), label="Decrease"),
    ]

    return rects, colors, legend_handles


# Map normalized values to color intensity
def scale_colors_treemap(area: float, max_area: float) -> float:
    vmin = 0.3
    vmax = 0.65
    return vmin + (area / max_area) * (vmax - vmin)


def draw_treemap_rects_with_labels(
    ax: plt.Axes,
    rects: list[dict],
    modules: list[FileDataEntry] | list[FileDataEntryPlatformVersion],
    colors: list[tuple[float, float, float, float]],
) -> None:
    """
    Draw treemap rectangles with their assigned colors and optional text labels.

    Args:
        ax: Matplotlib Axes to draw on.
        rects: List of rectangle dicts from squarify, each with 'x', 'y', 'dx', 'dy'.
        modules: List of modules associated with each rectangle (same order).
        colors: List of colors for each module (same order).
    """
    for rect, mod, color in zip(rects, modules, colors, strict=False):
        x, y, dx, dy = rect["x"], rect["y"], rect["dx"], rect["dy"]

        # Draw the rectangle with a white border
        ax.add_patch(plt.Rectangle((x, y), dx, dy, color=color, ec="white"))

        # Determine font size based on rectangle area
        MIN_FONT_SIZE = 6
        MAX_FONT_SIZE = 12
        FONT_SIZE_SCALE = 0.4
        AVG_SIDE = (dx * dy) ** 0.5  # Geometric mean
        font_size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, AVG_SIDE * FONT_SIZE_SCALE))

        # Determine the info for the labels
        name = mod["Name"]
        size_str = f"({mod['Size']})"

        # Estimate if there's enough space for text
        CHAR_WIDTH_FACTOR = 0.1  # Width of each character relative to font size
        CHAR_HEIGHT_FACTOR = 0.5  # Minimum height for readable text

        name_fits = (len(name) + 2) * font_size * CHAR_WIDTH_FACTOR < dx and dy > font_size * CHAR_HEIGHT_FACTOR
        size_fits = (len(size_str) + 2) * font_size * CHAR_WIDTH_FACTOR < dx
        both_fit = dy > font_size * CHAR_HEIGHT_FACTOR * 2  # Enough room for two lines

        # If the rectangle is too small, skip the label
        if dx < 5 or dy < 5:
            label = None

        # If the name doesn't fit, truncate it with "..."
        elif not name_fits and dx > 5:
            max_chars = int(dx / (font_size * CHAR_WIDTH_FACTOR)) - 2
            if max_chars >= 4:
                name = name[: max_chars - 3] + "..."
                name_fits = True

        # Build the label based on available space
        if name_fits and size_fits and both_fit:
            label = f"{name}\n{size_str}"  # Two-line label
        elif name_fits:
            label = name
        else:
            label = None

        # Draw label centered inside the rectangle
        if label:
            ax.text(
                x + dx / 2,
                y + dy / 2,
                label,
                va="center",
                ha="center",
                fontsize=font_size,
                color="black",
            )


class WrongDependencyFormat(Exception):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)


class GitRepo:
    """
    Clones the repo to a temp folder and deletes the folder on exit.
    """

    def __init__(self, url: Path | str) -> None:
        self.url = url
        self.repo_dir: str

    def __enter__(self):
        self.repo_dir = tempfile.mkdtemp()
        try:
            self._run("git status")
        except Exception:
            # If it is not already a repo
            self._run(f"git clone --quiet {self.url} {self.repo_dir}")
        return self

    def _run(self, command: str) -> list[str]:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True, cwd=self.repo_dir)
        return result.stdout.strip().split("\n")

    def get_module_commits(
        self, module_path: str, initial: Optional[str], final: Optional[str], time: Optional[str]
    ) -> list[str]:
        """
        Returns the list of commits (SHA) that modified a given module, filtered by time or commit range.

        Args:
            module_path: Integration name or path to the .deps/resolved file (for dependencies).
            initial: Optional initial commit hash.
            final: Optional final commit hash.
            time: Optional time filter (e.g. '2 weeks ago').

        Returns:
            List of commit SHAs (oldest to newest).
        """
        self._run("git fetch origin --quiet")
        self._run("git checkout origin/HEAD")
        try:
            if time:
                return self._run(f'git log --since="{time}" --reverse --pretty=format:%H -- {module_path}')
            elif not initial and not final:
                return self._run(f"git log --reverse --pretty=format:%H -- {module_path}")
            elif not final:
                return self._run(f"git log --reverse --pretty=format:%H {initial}..HEAD -- {module_path}")
            else:
                try:
                    self._run(f"git merge-base --is-ancestor {initial} {final}")
                except subprocess.CalledProcessError:
                    raise ValueError(f"Commit {initial} does not come before {final}")
                return self._run(f"git log --reverse --pretty=format:%H {initial}..{final} -- {module_path}")
        except subprocess.CalledProcessError as e:
            raise ValueError(
                "Failed to retrieve commit history.\n"
                "Make sure that the provided commits are correct and that your local repository is up to"
                "date with the remote"
            ) from e

    def checkout_commit(self, commit: str) -> None:
        try:
            self._run(f"git fetch --quiet --depth 1 origin {commit}")
        except subprocess.CalledProcessError as e:
            if e.returncode == 128:
                raise ValueError(
                    f"Failed to fetch commit '{commit}'.\n"
                    f"Make sure the provided commit hash is correct and that your local repository "
                    "is up to date with the remote\n"
                ) from e
        self._run(f"git checkout --quiet {commit}")

    def sparse_checkout_commit(self, commit_sha: str, module: str) -> None:
        self._run("git sparse-checkout init --cone")
        self._run(f"git sparse-checkout set {module}")
        self._run(f"git checkout {commit_sha}")

    def get_commit_metadata(self, commit: str) -> tuple[str, str, str]:
        result = self._run(f'git log -1 --date=format:"%b %d %Y" --pretty=format:"%ad\n%an\n%s" {commit}')
        date, author, message = result
        return date, author, message

    def get_creation_commit_module(self, integration: str) -> str:
        """
        Returns the first commit (SHA) where the given integration was introduced.
        """
        return self._run(f'git log --reverse --format="%H" -- {integration}')[0]

    def __exit__(
        self,
        exception_type: Optional[Type[BaseException]],
        exception_value: Optional[BaseException],
        exception_traceback: Optional[TracebackType],
    ) -> None:
        if self.repo_dir and os.path.exists(self.repo_dir):
            shutil.rmtree(self.repo_dir)
