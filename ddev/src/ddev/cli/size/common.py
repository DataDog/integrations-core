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
from typing import Dict, List, Literal, Optional, Set, Tuple, Type, TypedDict, Union, cast

import matplotlib.cm as cm
import matplotlib.pyplot as plt
import requests
import squarify
from matplotlib.patches import Patch

from ddev.cli.application import Application

'''
 Custom typed dictionaries
'''


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


def get_valid_platforms(repo_path: Union[Path, str]) -> Set[str]:
    """
    Extracts the platforms we support from the .deps/resolved file names.
    """

    resolved_path = os.path.join(repo_path, os.path.join(repo_path, ".deps", "resolved"))
    platforms = []
    for file in os.listdir(resolved_path):
        platforms.append("_".join(file.split("_")[:-1]))
    return set(platforms)


def get_valid_versions(repo_path: Union[Path, str]) -> Set[str]:
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


def convert_to_human_readable_size(size_bytes: float) -> str:
    """
    Converts a size in bytes into a human-readable string (B, KB, MB, GB, or TB)
    """
    for unit in [" B", " KB", " MB", " GB"]:
        if abs(size_bytes) < 1024:
            return str(round(size_bytes, 2)) + unit
        size_bytes /= 1024
    return str(round(size_bytes, 2)) + " TB"


def is_valid_integration(path: str, included_folder: str, ignored_files: Set[str], git_ignore: List[str]) -> bool:
    """
    Determines whether a given file path corresponds to a valid integration file.

    Args:
        path: The file path to check.
        included_folder: Required subfolder (e.g. 'datadog_checks') that marks valid integrations.
        ignored_files: Set of filenames or patterns to exclude.
        git_ignore: List of .gitignore patterns to exclude.

    Returns:
        True if the file should be considered part of a valid integration, False otherwise.
    """
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


def is_correct_dependency(platform: str, version: str, name: str) -> bool:
    """
    Checks whether a dependency filename matches a given platform and Python version.
    """

    return platform in name and version in name


def print_json(
    app: Application,
    i: Optional[int],
    n_iterations: Optional[int],
    printed_yet: bool,
    modules: (
        List[FileDataEntry]
        | List[FileDataEntryPlatformVersion]
        | List[CommitEntryWithDelta]
        | List[CommitEntryPlatformWithDelta]
    ),
) -> None:
    """
    Prints a list of data entries as part of a JSON array.

    This function is designed to be called multiple times, and ensures that:
      - The opening bracket "[" is printed only once at the start (when i is None or 0).
      - Each valid entry is printed on a separate line using JSON format.
      - Commas are inserted appropriately between entries, but not before the first one.
      - The closing bracket "]" is printed only at the final call (when i == n_iterations - 1).

    Args:
        app: Application instance used to display output.
        i: Index of the current batch of data being printed. If None or 0, this is the first chunk.
        n_iterations: Total number of iterations (chunks). Used to detect the last chunk.
        printed_yet: Whether at least one entry has already been printed before this call.
        modules: List of dictionaries to print. Only non-empty entries are included.
    """

    if not i:
        app.display("[")

    for idx, row in enumerate(modules):
        if any(str(value).strip() not in ("", "0", "0001-01-01") for value in row.values()):
            if printed_yet or (i != 0 and idx != 0):
                app.display(",")
            app.display(json.dumps(row, default=str))
            printed_yet = True

    if not n_iterations or i == n_iterations - 1:
        app.display("]")


def print_csv(
    app: Application,
    i: Optional[int],
    modules: (
        List[FileDataEntry]
        | List[FileDataEntryPlatformVersion]
        | List[CommitEntryWithDelta]
        | List[CommitEntryPlatformWithDelta]
    ),
) -> None:
    """
    Prints a list of data entries in CSV format.

    This function is designed to be called multiple times, and ensures that:
      - The headers are printed only once at the start (when i is None or 0).
      - Each valid entry is printed on a separate line using CSV format.
    Args:
        app: Application instance used to display output.
        i: Index of the current batch of data being printed. If None or 0, this is the first chunk.
        modules: List of dictionaries to print. Only non-empty entries are included.
    """
    headers = [k for k in modules[0].keys() if k not in ["Size", "Delta"]]
    if not i:
        app.display(",".join(headers))

    for row in modules:
        if any(str(value).strip() not in ("", "0", "0001-01-01") for value in row.values()):
            app.display(",".join(format(str(row.get(h, ""))) for h in headers))


def format(s: str) -> str:
    """
    Adds brackets to a value if it has a comma inside for the CSV
    """
    return f'"{s}"' if "," in s else s


def print_markdown(
    app: Application,
    title: str,
    modules: (
        List[FileDataEntry]
        | List[FileDataEntryPlatformVersion]
        | List[CommitEntryWithDelta]
        | List[CommitEntryPlatformWithDelta]
    ),
) -> None:
    """
    Prints a list of entries as a Markdown table.
    Only non-empty tables are printed.
    """
    if any(str(value).strip() not in ("", "0", "0001-01-01") for value in modules[0].values()):  # table is not empty
        headers = [k for k in modules[0].keys() if "Bytes" not in k]
        app.display(f"### {title}")
        app.display("| " + " | ".join(headers) + " |")
        app.display("| " + " | ".join("---" for _ in headers) + " |")

        for row in modules:
            app.display("| " + " | ".join(format(str(row.get(h, ""))) for h in headers) + " |")


def print_table(
    app: Application,
    mode: str,
    modules: (
        List[FileDataEntry]
        | List[FileDataEntryPlatformVersion]
        | List[CommitEntryWithDelta]
        | List[CommitEntryPlatformWithDelta]
    ),
) -> None:
    """
    Prints a list of entries as a Rich table.
    Only non-empty tables are printed.
    """
    # if any(str(value).strip() not in ("", "0", "0001-01-01") for value in modules[0].values()): # table is not empty
    columns = [col for col in modules[0].keys() if "Bytes" not in col]
    modules_table: Dict[str, Dict[int, str]] = {col: {} for col in columns}
    for i, row in enumerate(modules):
        if any(str(value).strip() not in ("", "0", "0001-01-01") for value in row.values()):
            for key in columns:
                modules_table[key][i] = str(row.get(key, ""))

    app.display_table(mode, modules_table)


def plot_treemap(
    modules: List[FileDataEntry] | List[FileDataEntryPlatformVersion],
    title: str,
    show: bool,
    mode: Literal["status", "diff"] = "status",
    path: Optional[str] = None,
) -> None:
    """
    Generates and displays or saves a treemap visualization of module sizes.

    The plot layout is computed using the size of each module (in bytes), and color is used to
    encode either the type of module or the direction/magnitude of size change, depending on the mode.

    - Modules with very small area may not show labels to avoid overlap.
    - Labels display module name and size if space allows.
    - Color intensity reflects relative size (or change) within its group.
    - A legend is added depending on the selected mode.

    Args:
        modules: List of module entries. Each entry must contain at least:
            - 'Name': The module name,
            - 'Size_Bytes': Module size in bytes (can be negative in 'diff' mode),
            - 'Size': Human-readable size string,
            - 'Type': Either 'Integration' or 'Dependency'.
        title: Title to display at the top of the plot.
        show: If True, the plot is shown interactively using matplotlib.
        mode:
            - 'status': Shows the current sizes of modules.
              Integrations and dependencies are grouped and colored separately (Purples/Reds),
              with size intensity mapped to color darkness.
            - 'diff': Shows the size change between two commits.
              Positive changes are colored in Oranges, negative changes in Blues.
              The plot is split in half: left for decreases, right for increases.
        path: Optional path to save the plot as a PNG file. If not provided, nothing is saved.
    """
    if not any(str(value).strip() not in ("", "0") for value in modules[0].values()):  # table is empty
        return

    # Convert sizes to absolute values for layout computation
    sizes = [abs(mod["Size_Bytes"]) for mod in modules]

    # Initialize figure and axis
    plt.figure(figsize=(12, 8))
    ax = plt.gca()
    ax.set_axis_off()

    # Compute layout rectangles based on size
    rects = squarify.normalize_sizes(sizes, 100, 100)
    rects = squarify.squarify(rects, 0, 0, 100, 100)

    colors = []

    if mode == "status":
        # Separate modules by type
        integrations = [mod for mod in modules if mod["Type"] == "Integration"]
        dependencies = [mod for mod in modules if mod["Type"] == "Dependency"]

        # Normalize sizes within each group
        def normalize(mods):
            if not mods:
                return []
            sizes = [mod["Size_Bytes"] for mod in mods]
            min_size = min(sizes)
            max_size = max(sizes)
            range_size = max_size - min_size or 1
            return [(s - min_size) / range_size for s in sizes]

        norm_int = normalize(integrations)
        norm_dep = normalize(dependencies)

        # Map normalized values to color intensity
        def scale(val, vmin=0.3, vmax=0.85):
            return vmin + val * (vmax - vmin)

        cmap_int = cm.get_cmap("Purples")
        cmap_dep = cm.get_cmap("Reds")

        # Assign colors based on type and normalized size
        for mod in modules:
            if mod["Type"] == "Integration":
                idx = integrations.index(mod)
                colors.append(cmap_int(scale(norm_int[idx], 0.3, 0.6)))
            elif mod["Type"] == "Dependency":
                idx = dependencies.index(mod)
                colors.append(cmap_dep(scale(norm_dep[idx], 0.3, 0.85)))
            else:
                colors.append("#999999")

    elif mode == "diff":
        # Separate modules by positive and negative size change
        cmap_pos = cm.get_cmap("Oranges")
        cmap_neg = cm.get_cmap("Blues")

        positives = [mod for mod in modules if cast(int, mod["Size_Bytes"]) > 0]
        negatives = [mod for mod in modules if cast(int, mod["Size_Bytes"]) < 0]

        sizes_pos = [mod["Size_Bytes"] for mod in positives]
        sizes_neg = [abs(mod["Size_Bytes"]) for mod in negatives]

        sum_pos = sum(sizes_pos)
        sum_neg = sum(sizes_neg)

        canvas_area = 50 * 100

        # Determine dominant side and scale layout accordingly
        if sum_pos >= sum_neg:
            norm_sizes_pos = [s / sum_pos * canvas_area for s in sizes_pos]
            norm_sizes_neg = [s / sum_pos * canvas_area for s in sizes_neg]
            rects_pos = squarify.squarify(norm_sizes_pos, 50, 0, 50, 100)
            rects_neg = squarify.squarify(norm_sizes_neg, 0, 0, 50, 100)
        else:
            norm_sizes_neg = [s / sum_neg * canvas_area for s in sizes_neg]
            norm_sizes_pos = [s / sum_neg * canvas_area for s in sizes_pos]
            rects_neg = squarify.squarify(norm_sizes_neg, 0, 0, 50, 100)
            rects_pos = squarify.squarify(norm_sizes_pos, 50, 0, 50, 100)

        # Merge layout and module lists for unified drawing
        rects = rects_neg + rects_pos
        modules = negatives + positives

        # Compute color intensity for each module
        def rescale_intensity(val, min_val=0.3, max_val=0.8):
            return min_val + (max_val - min_val) * val

        max_size = max(sizes_pos + sizes_neg) or 1
        colors = []

        for mod in negatives:
            raw = abs(mod["Size_Bytes"]) / max_size
            intensity = rescale_intensity(raw)
            colors.append(cmap_neg(intensity))

        for mod in positives:
            raw = mod["Size_Bytes"] / max_size
            intensity = rescale_intensity(raw)
            colors.append(cmap_pos(intensity))

    # Manual treemap layout and coloring to personalize labels
    for rect, mod, color in zip(rects, modules, colors, strict=False):
        x, y, dx, dy = rect["x"], rect["y"], rect["dx"], rect["dy"]
        ax.add_patch(plt.Rectangle((x, y), dx, dy, color=color, ec="white"))

        # Determine font size based on rectangle area
        MIN_FONT_SIZE = 6
        MAX_FONT_SIZE = 12
        FONT_SIZE_SCALE = 0.4
        AVG_SIDE = (dx * dy) ** 0.5
        font_size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, AVG_SIDE * FONT_SIZE_SCALE))
        name = mod["Name"]
        size_str = f"({mod['Size']})"

        # Check whether text fits inside the rectangle
        CHAR_WIDTH_FACTOR = 0.1
        CHAR_HEIGHT_FACTOR = 0.5
        name_fits = (len(name) + 2) * font_size * CHAR_WIDTH_FACTOR < dx and dy > font_size * CHAR_HEIGHT_FACTOR
        size_fits = (len(size_str) + 2) * font_size * CHAR_WIDTH_FACTOR < dx
        both_fit = dy > font_size * CHAR_HEIGHT_FACTOR * 2

        # Possibly truncate name if it doesn't fit
        if dx < 5 or dy < 5:
            label = None
        elif not name_fits and dx > 5:
            max_chars = int(dx / (font_size * CHAR_WIDTH_FACTOR)) - 2
            if 4 <= max_chars:
                name = name[: max_chars - 3] + "..."
                name_fits = True

        # Construct label if there's space
        if name_fits and size_fits and both_fit:
            label = f"{name}\n{size_str}"
        elif name_fits:
            label = name
        else:
            label = None

        # Draw label
        if label:
            ax.text(x + dx / 2, y + dy / 2, label, va="center", ha="center", fontsize=font_size, color="black")

    # Finalize layout and show/save plot
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)

    plt.title(title, fontsize=16)

    if mode == "status":
        legend_handles = [
            Patch(color=cm.get_cmap("Purples")(0.6), label="Integration"),
            Patch(color=cm.get_cmap("Reds")(0.6), label="Dependency"),
        ]
    elif mode == "diff":
        legend_handles = [
            Patch(color=cm.get_cmap("Oranges")(0.7), label="Increase"),
            Patch(color=cm.get_cmap("Blues")(0.7), label="Decrease"),
        ]

    plt.legend(handles=legend_handles, title="Type", loc="center left", bbox_to_anchor=(1.0, 0.5))
    plt.subplots_adjust(right=0.8)
    plt.tight_layout()

    if show:
        plt.show()
    if path:
        plt.savefig(path, bbox_inches="tight", format="png")


def get_dependencies_sizes(
    deps: List[str], download_urls: List[str], versions: List[str], compressed: bool
) -> List[FileDataEntry]:
    """
    Calculates the sizes of dependencies, either compressed or uncompressed.

    Args:
        deps: List of dependency names.
        download_urls: Corresponding download URLs for the dependencies.
        versions: Corresponding version strings for the dependencies.
        compressed: If True, use the Content-Length from the HTTP headers.
                    If False, download, extract, and compute actual uncompressed size.

    Returns:
        A list of FileDataEntry dictionaries with name, version, size in bytes, and human-readable size.
    """
    file_data: List[FileDataEntry] = []
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


def get_files(repo_path: str | Path, compressed: bool) -> List[FileDataEntry]:
    """
    Calculates integration file sizes and versions from a repository.

    Args:
        repo_path: Path to the repository root.
        compressed: If True, measure compressed file sizes. If False, measure uncompressed sizes.

    Returns:
        A list of FileDataEntry dictionaries with name, version, size in bytes, and human-readable size.
    """
    ignored_files = {"datadog_checks_dev", "datadog_checks_tests_helper"}
    git_ignore = get_gitignore_files(repo_path)
    included_folder = "datadog_checks/"

    integration_sizes: Dict[str, int] = {}
    integration_versions: Dict[str, str] = {}

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


def get_dependencies_list(file_path: str) -> Tuple[List[str], List[str], List[str]]:
    """
    Parses a dependency file and extracts the dependency names, download URLs, and versions.

    Args:
        file_path: Path to the file containing the dependencies.

    Returns:
        A tuple of three lists:
            - List of dependency names
            - List of download URLs
            - List of extracted version strings
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


def format_modules(
    modules: List[FileDataEntry], platform: str, version: str, i: Optional[int]
) -> List[FileDataEntryPlatformVersion] | List[FileDataEntry]:
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
    if modules == [] and i is None:
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
    elif i is not None:
        new_modules: List[FileDataEntryPlatformVersion] = [
            {**entry, "Platform": platform, "Python_Version": version} for entry in modules
        ]
        return new_modules
    else:
        return modules


def extract_version_from_about_py(path: str) -> str:
    """
    Extracts the __version__ string from a given __about__.py file.

    Args:
        path: Path to the __about__.py file.

    Returns:
        The extracted version string if found, otherwise an empty string.
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


def get_dependencies(repo_path: str | Path, platform: str, version: str, compressed: bool) -> List[FileDataEntry]:
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


def get_gitignore_files(repo_path: str | Path) -> List[str]:
    """
    Returns the list of non-commented files from the .gitignore file.
    """
    gitignore_path = os.path.join(repo_path, ".gitignore")
    with open(gitignore_path, "r", encoding="utf-8") as file:
        gitignore_content = file.read()
        ignored_patterns = [
            line.strip() for line in gitignore_content.splitlines() if line.strip() and not line.startswith("#")
        ]
        return ignored_patterns


def compress(file_path: str) -> int:
    '''
    Returns the compressed size (in bytes) of a file using zlib
    '''
    compressor = zlib.compressobj()
    compressed_size = 0
    # original_size = os.path.getsize(file_path)
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):  # Read in 8KB chunks
            compressed_chunk = compressor.compress(chunk)
            compressed_size += len(compressed_chunk)
        compressed_size += len(compressor.flush())
    return compressed_size


class WrongDependencyFormat(Exception):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)


class GitRepo:
    """
    Clones the repo to a temp folder and deletes the folder on exit.
    """

    def __init__(self, url: Union[Path, str]) -> None:
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

    def _run(self, command: str) -> List[str]:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True, cwd=self.repo_dir)
        return result.stdout.strip().split("\n")

    def get_module_commits(
        self, module_path: str, initial: Optional[str], final: Optional[str], time: Optional[str]
    ) -> List[str]:
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

    def get_commit_metadata(self, commit: str) -> Tuple[str, str, str]:
        result = self._run(f'git log -1 --date=format:"%b %d %Y" --pretty=format:"%ad\n%an\n%s" {commit}')
        date, author, message = result
        return date, author, message

    def get_creation_commit_module(self, integration: str) -> str:
        '''
        Returns the first commit (SHA) where the given integration was introduced.
        '''
        return self._run(f'git log --reverse --format="%H" -- {integration}')[0]

    def __exit__(
        self,
        exception_type: Optional[Type[BaseException]],
        exception_value: Optional[BaseException],
        exception_traceback: Optional[TracebackType],
    ) -> None:
        if self.repo_dir and os.path.exists(self.repo_dir):
            shutil.rmtree(self.repo_dir)
