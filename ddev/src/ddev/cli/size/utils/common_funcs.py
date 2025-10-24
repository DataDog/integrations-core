# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
import zlib
from datetime import date
from enum import StrEnum
from functools import cache
from types import TracebackType
from typing import TYPE_CHECKING, Optional, Type, TypedDict

import requests
import squarify
from typing_extensions import Literal, NotRequired

from ddev.cli.application import Application
from ddev.cli.size.utils.size_model import Size, Sizes, convert_to_human_readable_size
from ddev.utils.fs import Path
from ddev.utils.toml import load_toml_file

METRIC_VERSION = 1

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.patches import Patch


class SizeMode(StrEnum):
    STATUS = "status"
    DIFF = "diff"


class DependencyEntry(TypedDict):
    compressed: NotRequired[int]  # Size in bytes
    uncompressed: NotRequired[int]  # Size in bytes
    version: str  # Version of the Dependency


class DeltaTypeGroup(TypedDict):
    Modules: Sizes
    Total: int


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


class CLIParameters(TypedDict):
    app: Application  # Main application instance for CLI operations
    platform: NotRequired[str]  # Target platform for analysis (e.g. linux-aarch64)
    py_version: NotRequired[str]  # Target Python version for analysis
    compressed: bool  # Whether to analyze compressed file sizes
    format: Optional[list[str]]  # Output format options (png, csv, markdown, json)
    show_gui: bool  # Whether to display interactive visualization
    quality_gate_threshold: NotRequired[float | None]  # Quality gate threshold for the size difference
    to_dd_org: NotRequired[str | None]  # Datadog organization name
    to_dd_key: NotRequired[str | None]  # Datadog API key
    to_dd_site: NotRequired[str | None]  # Datadog site
    combinations: NotRequired[list[tuple[str, str]]]  # List of platform and Python version combinations to analyze


class CLIParametersTimeline(TypedDict):
    app: Application  # Main application instance for CLI operations
    module: str  # Name of module to analyze
    threshold: Optional[int]  # Minimum size threshold for filtering
    compressed: bool  # Whether to analyze compressed file sizes
    format: Optional[list[str]]  # Output format options (png, csv, markdown, json)
    show_gui: bool  # Whether to display interactive visualization


class InitialParametersTimelineIntegration(CLIParametersTimeline):
    type: Literal["integration"]  # Specifies this is for integration analysis
    first_commit: str  # Starting commit hash for timeline analysis
    platform: None  # Platform not needed for integration analysis


class InitialParametersTimelineDependency(CLIParametersTimeline):
    type: Literal["dependency"]  # Specifies this is for dependency analysis
    first_commit: None  # No commit needed for dependency analysis
    platform: str  # Target platform for dependency analysis


def get_valid_platforms(repo_path: Path | str, versions: set[str]) -> set[str]:
    """
    Extracts the platforms we support from the .deps/resolved file names.
    """
    resolved_path = os.path.join(repo_path, ".deps", "resolved")
    platforms = []
    for file in os.listdir(resolved_path):
        if any(version in file for version in versions):
            platforms.append("_".join(file.split("_")[:-1]))
    return set(platforms)


def get_valid_versions(repo_path: Path | str) -> set[str]:
    """
    Extracts the Python versions we support from the .deps/resolved file names.
    """
    resolved_path = os.path.join(repo_path, ".deps", "resolved")
    versions = []
    pattern = re.compile(r"\d+\.\d+")
    for file in os.listdir(resolved_path):
        match = pattern.search(file)
        if match:
            versions.append(match.group())
    return set(versions)


# Integrations sizes
def is_valid_integration_file(
    path: str,
    repo_path: str,
    ignored_files: set[str] | None = None,
    included_folder: str | None = None,
    git_ignore: list[str] | None = None,
) -> bool:
    """
    Check if a file would be packaged with an integration.

    Used to estimate integration package size by excluding:
    - Hidden files (starting with ".")
    - Files outside "datadog_checks"
    - Helper/test-only packages (e.g. datadog_checks_dev)
    - Files ignored by .gitignore

    Args:
        path (str): File path to check.
        repo_path (str): Repository root, for loading .gitignore rules.

    Returns:
        bool: True if the file would be packaged, False otherwise.
    """
    if ignored_files is None:
        ignored_files = {
            "datadog_checks_dev",
            "datadog_checks_tests_helper",
        }

    if included_folder is None:
        included_folder = "datadog_checks" + os.sep

    if git_ignore is None:
        git_ignore = get_gitignore_files(repo_path)
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


def get_files(repo_path: str | Path, compressed: bool, py_version: str, platform: str) -> Sizes:
    """
    Calculates integration file sizes and versions from a repository.
    Only takes into account integrations with a valid version looking at the pyproject.toml file
    The pyproject.toml file should have a classifier with this format:
        classifiers = [
            ...
            "Programming Language :: Python :: 3.13",
            ...
        ]
    """
    integration_sizes: dict[str, int] = {}
    integration_versions: dict[str, str] = {}
    py_major_version = py_version.split(".")[0]

    for root, _, files in os.walk(repo_path):
        integration_name = str(os.path.relpath(root, repo_path).split(os.sep)[0])

        if not check_python_version(str(repo_path), integration_name, py_major_version):
            continue
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, repo_path)
            if not is_valid_integration_file(relative_path, str(repo_path)):
                continue

            size = compress(file_path) if compressed else os.path.getsize(file_path)
            integration_sizes[integration_name] = integration_sizes.get(integration_name, 0) + size

            if integration_name not in integration_versions and file == "__about__.py":
                version = extract_version_from_about_py(file_path)
                integration_versions[integration_name] = version

    return Sizes(
        [
            Size(
                name=name,
                version=integration_versions.get(name, ""),
                size_bytes=size,
                type="Integration",
                platform=platform,
                python_version=py_version,
            )
            for name, size in integration_sizes.items()
        ]
    )


def check_python_version(repo_path: str, integration_name: str, py_major_version: str) -> bool:
    pyproject_path = os.path.join(repo_path, integration_name, "pyproject.toml")
    if os.path.exists(pyproject_path):
        pyproject = load_toml_file(pyproject_path)
        if "project" not in pyproject or "classifiers" not in pyproject["project"]:
            return False
        classifiers = pyproject["project"]["classifiers"]
        integration_py_version = ""
        pattern = re.compile(r"Programming Language :: Python :: (\d+)")
        for classifier in classifiers:
            match = pattern.match(classifier)
            if match:
                integration_py_version = match.group(1)
                return integration_py_version == py_major_version
    return False


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


# Dependency sizes
def is_correct_dependency(platform: str, version: str, name: str) -> bool:
    # The name of the dependency file is in the format of {platform}_{version}.txt e.g. linux-aarch64_3.12.txt
    _platform, _version = name.rsplit(".", 1)[0].rsplit("_", 1)
    return platform == _platform and version == _version


def get_dependencies(repo_path: str | Path, platform: str, py_version: str, compressed: bool) -> Sizes:
    """
    Gets the list of dependencies for a given platform and Python version and returns a Sizes object.
    """
    resolved_path = Path(repo_path) / ".deps" / "resolved"
    for filename in resolved_path.iterdir():
        if filename.is_file() and is_correct_dependency(platform, py_version, filename.name):
            deps, download_urls, versions = get_dependencies_list(filename)
            return get_dependencies_sizes(deps, download_urls, versions, compressed, platform, py_version)
    return Sizes([])


def get_dependencies_list(file_path: Path) -> tuple[list[str], list[str], list[str]]:
    """
    Parses a dependency file and extracts the dependency names, download URLs, and versions.
    """
    download_urls = []
    deps = []
    versions = []
    file_content = file_path.read_text(encoding="utf-8")
    pattern = re.compile(r"([\w\-\d\.]+) @ (https?://[^\s#]+)")
    for line in file_content.splitlines():
        match = pattern.search(line)
        if not match:
            raise WrongDependencyFormat("The dependency format 'name @ link' is no longer supported.")
        name = match.group(1)
        url = match.group(2)

        deps.append(name)
        download_urls.append(url)
        version_match = re.search(rf"{re.escape(name)}/[^/]+?-([0-9]+(?:\.[0-9]+)*)-", url)
        if version_match:
            versions.append(version_match.group(1))
        else:
            versions.append("")

    return deps, download_urls, versions


def get_dependencies_sizes(
    deps: list[str], download_urls: list[str], versions: list[str], compressed: bool, platform: str, py_version: str
) -> Sizes:
    file_data: Sizes = Sizes([])
    for dep, url, version in zip(deps, download_urls, versions, strict=False):
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            wheel_data = response.content

        with tempfile.TemporaryDirectory() as tmpdir:
            wheel_path = Path(tmpdir) / "package"
            with open(wheel_path, "wb") as f:
                f.write(wheel_data)
            if compressed:
                with zipfile.ZipFile(wheel_path, "r") as zip_ref:
                    size = sum(
                        zinfo.compress_size
                        for zinfo in zip_ref.infolist()
                        if not is_excluded_from_wheel(zinfo.filename)
                    )
            else:
                extract_path = Path(tmpdir) / "extracted"
                with zipfile.ZipFile(wheel_path, "r") as zip_ref:
                    zip_ref.extractall(extract_path)

                size = 0
                for dirpath, _, filenames in os.walk(extract_path):
                    rel_dir = os.path.relpath(dirpath, extract_path)
                    if is_excluded_from_wheel(rel_dir):
                        continue
                    for name in filenames:
                        file_path = os.path.join(dirpath, name)
                        rel_file = os.path.relpath(file_path, extract_path)
                        if is_excluded_from_wheel(rel_file):
                            continue
                        size += os.path.getsize(file_path)

        file_data.append(
            Size(
                name=str(dep),
                version=version,
                size_bytes=int(size),
                type="Dependency",
                platform=platform,
                python_version=py_version,
            )
        )

    return file_data


def is_excluded_from_wheel(path: str) -> bool:
    """
    These files are excluded from the wheel in the agent build:
    https://github.com/DataDog/datadog-agent/blob/main/omnibus/config/software/datadog-agent-integrations-py3.rb
    In order to have more accurate results, this files are excluded when computing the size of the dependencies while
    the wheels still include them.
    """
    excluded_test_paths = [
        os.path.normpath(path)
        for path in [
            "idlelib/idle_test",
            "bs4/tests",
            "Cryptodome/SelfTest",
            "gssapi/tests",
            "keystoneauth1/tests",
            "openstack/tests",
            "os_service_types/tests",
            "pbr/tests",
            "pkg_resources/tests",
            "psutil/tests",
            "securesystemslib/_vendor/ed25519/test_data",
            "setuptools/_distutils/tests",
            "setuptools/tests",
            "simplejson/tests",
            "stevedore/tests",
            "supervisor/tests",
            "test",  # cm-client
            "vertica_python/tests",
            "websocket/tests",
        ]
    ]

    type_annot_libraries = [
        "krb5",
        "Cryptodome",
        "ddtrace",
        "pyVmomi",
        "gssapi",
    ]
    rel_path = Path(path).as_posix()

    # Test folders
    for test_folder in excluded_test_paths:
        if rel_path == test_folder or rel_path.startswith(test_folder + os.sep):
            return True

    # Python type annotations
    path_parts = Path(rel_path).parts
    if path_parts:
        dependency_name = path_parts[0]
        if dependency_name in type_annot_libraries:
            if path.endswith(".pyi") or os.path.basename(path) == "py.typed":
                return True

    return False


def export_format(
    app: Application,
    format: list[str],
    modules: Sizes,
    mode: SizeMode,
    platform: str | None,
    py_version: str | None,
    compressed: bool,
) -> None:
    size_type = "compressed" if compressed else "uncompressed"
    name = f"{mode.value}_{size_type}"
    if platform:
        name += f"_{platform}"
    if py_version:
        name += f"_{py_version}"
    for output_format in format:
        if output_format == "csv":
            csv_filename = f"{name}.csv"
            modules.export_to_csv(app, Path(csv_filename))

        elif output_format == "json":
            json_filename = f"{name}.json"
            modules.export_to_json(app, Path(json_filename))

        elif output_format == "markdown":
            markdown_filename = f"{name}.md"
            modules.export_to_markdown(app, Path(markdown_filename))


def plot_treemap(
    app: Application,
    modules: Sizes,
    title: str,
    show: bool,
    mode: SizeMode,
    path: Optional[str] = None,
) -> None:
    import matplotlib.pyplot as plt

    if not modules:
        return

    # Initialize figure and axis
    plt.figure(figsize=(12, 8))
    ax = plt.gca()
    ax.set_axis_off()

    # Calculate the rectangles
    if mode is SizeMode.STATUS:
        rects, colors, legend_handles = plot_status_treemap(modules)

    if mode is SizeMode.DIFF:
        rects, colors, legend_handles = plot_diff_treemap(modules)

    draw_treemap_rects_with_labels(ax, rects, modules, colors)

    # Finalize layout and show/save plot
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)

    plt.title(title, fontsize=16)

    plt.legend(handles=legend_handles, title="Type", loc="center left", bbox_to_anchor=(1.0, 0.5))
    plt.subplots_adjust(right=0.8)
    plt.tight_layout()

    if path:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        plt.savefig(path, bbox_inches="tight", format="png")
        app.display(f"Treemap saved to {path}")
    if show:
        plt.show()


def plot_status_treemap(
    modules: Sizes,
) -> tuple[list[dict[str, float]], list[tuple[float, float, float, float]], list[Patch]]:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    # Calculate the area of the rectangles
    sizes = [mod.size_bytes for mod in modules.root]
    norm_sizes = squarify.normalize_sizes(sizes, 100, 100)
    rects = squarify.squarify(norm_sizes, 0, 0, 100, 100)

    # Define the colors for each type
    cmap_int = plt.get_cmap("Purples")
    cmap_dep = plt.get_cmap("Reds")

    # Assign colors based on type and normalized size
    colors = []
    max_area = max(norm_sizes) or 1
    for mod, area in zip(modules.root, norm_sizes, strict=False):
        intensity = scale_colors_treemap(area, max_area)
        if mod.type == "Integration":
            colors.append(cmap_int(intensity))
        elif mod.type == "Dependency":
            colors.append(cmap_dep(intensity))
        else:
            colors.append("#999999")
    # Define the legend
    legend_handles = [
        Patch(color=plt.get_cmap("Purples")(0.6), label="Integration"),
        Patch(color=plt.get_cmap("Reds")(0.6), label="Dependency"),
    ]
    return rects, colors, legend_handles


def plot_diff_treemap(
    modules: Sizes,
) -> tuple[list[dict[str, float]], list[tuple[float, float, float, float]], list[Patch]]:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    # Define the colors for each type
    cmap_pos = plt.get_cmap("Oranges")
    cmap_neg = plt.get_cmap("Blues")

    # Separate in negative and positive differences
    positives = [mod for mod in modules.root if mod.size_bytes > 0]
    negatives = [mod for mod in modules.root if mod.size_bytes < 0]

    sizes_pos = [mod.size_bytes for mod in positives]
    sizes_neg = [abs(mod.size_bytes) for mod in negatives]

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
    modules = Sizes(negatives + positives)

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
        Patch(color=plt.get_cmap("Oranges")(0.7), label="Increase"),
        Patch(color=plt.get_cmap("Blues")(0.7), label="Decrease"),
    ]

    return rects, colors, legend_handles


def scale_colors_treemap(area: float, max_area: float) -> float:
    vmin = 0.3
    vmax = 0.65
    return vmin + (area / max_area) * (vmax - vmin)


def draw_treemap_rects_with_labels(
    ax: Axes,
    rects: list[dict],
    modules: Sizes,
    colors: list[tuple[float, float, float, float]],
) -> None:
    from matplotlib.patches import Rectangle

    """
    Draw treemap rectangles with their assigned colors and optional text labels.

    Args:
        ax: Matplotlib Axes to draw on.
        rects: List of rectangle dicts from squarify, each with 'x', 'y', 'dx', 'dy'.
        modules: List of modules associated with each rectangle (same order).
        colors: List of colors for each module (same order).
    """
    for rect, mod, color in zip(rects, modules.root, colors, strict=False):
        x, y, dx, dy = rect["x"], rect["y"], rect["dx"], rect["dy"]

        # Draw the rectangle with a white border
        ax.add_patch(Rectangle((x, y), dx, dy, color=color, ec="white"))

        # Determine font size based on rectangle area
        MIN_FONT_SIZE = 6
        MAX_FONT_SIZE = 12
        FONT_SIZE_SCALE = 0.4
        AVG_SIDE = (dx * dy) ** 0.5  # Geometric mean
        font_size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, AVG_SIDE * FONT_SIZE_SCALE))

        # Determine the info for the labels
        name = mod.name
        size_str = f"({mod.size})"

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


def send_metrics_to_dd(
    app: Application,
    sizes: Sizes,
    org: str | None,
    key: str | None,
    site: str | None,
    compressed: bool,
    mode: SizeMode,
    commits: list[str] | None = None,
) -> None:
    from datadog_api_client import ApiClient, Configuration
    from datadog_api_client.v2.api.metrics_api import MetricsApi
    from datadog_api_client.v2.model.metric_intake_type import MetricIntakeType
    from datadog_api_client.v2.model.metric_payload import MetricPayload
    from datadog_api_client.v2.model.metric_point import MetricPoint
    from datadog_api_client.v2.model.metric_series import MetricSeries

    metric_name = "datadog.agent_integrations"
    size_type = "compressed" if compressed else "uncompressed"
    dd_site = site if site else "datadoghq.com"
    config_file_info = app.config.orgs.get(org, {}) if org else {'api_key': key, 'site': dd_site}

    if "api_key" not in config_file_info or config_file_info["api_key"] is None or config_file_info["api_key"] == "":
        raise RuntimeError("No API key found in config file")
    if "site" not in config_file_info or config_file_info["site"] is None or config_file_info["site"] == "":
        raise RuntimeError("No site found in config file")

    timestamp, message, tickets, prs = get_commit_data(commits[-1]) if commits else get_commit_data()

    metrics = []
    n_integrations_metrics = []
    n_dependencies_metrics = []

    n_integrations: dict[tuple[str, str], int] = {}
    n_dependencies: dict[tuple[str, str], int] = {}

    gauge_type = MetricIntakeType.GAUGE

    for item in sizes.root:
        delta_type = item.delta_type
        metrics.append(
            MetricSeries(
                metric=f"{metric_name}.size_{mode.value}",
                type=gauge_type,
                points=[MetricPoint(timestamp=timestamp, value=item.size_bytes)],
                tags=[
                    f"module_name:{item.name}",
                    f"module_type:{item.type}",
                    f"name_type:{item.type}({item.name})",
                    f"python_version:{item.python_version}",
                    f"module_version:{item.version}",
                    f"platform:{item.platform}",
                    "team:agent-integrations",
                    f"compression:{size_type}",
                    f"metrics_version:{METRIC_VERSION}",
                    f"jira_ticket:{tickets[0]}",
                    f"pr_number:{prs[-1]}",
                    f"commit_message:{message}",
                    f"delta_Type:{delta_type}",
                ],
            )
        )
        if mode is SizeMode.STATUS:
            key_count = (item.platform, item.python_version)
            if key_count not in n_integrations:
                n_integrations[key_count] = 0
            if key_count not in n_dependencies:
                n_dependencies[key_count] = 0
            if item.type == 'Integration':
                n_integrations[key_count] += 1
            elif item.type == 'Dependency':
                n_dependencies[key_count] += 1

    if mode is SizeMode.STATUS:
        for (platform, py_version), count in n_integrations.items():
            n_integrations_metrics.append(
                MetricSeries(
                    metric=f"{metric_name}.integration_count",
                    type=gauge_type,
                    points=[MetricPoint(timestamp=timestamp, value=count)],
                    tags=[
                        f"platform:{platform}",
                        f"python_version:{py_version}",
                        "team:agent-integrations",
                        f"metrics_version:{METRIC_VERSION}",
                    ],
                )
            )
        for (platform, py_version), count in n_dependencies.items():
            n_dependencies_metrics.append(
                MetricSeries(
                    metric=f"{metric_name}.dependency_count",
                    type=gauge_type,
                    points=[MetricPoint(timestamp=timestamp, value=count)],
                    tags=[
                        f"platform:{platform}",
                        f"python_version:{py_version}",
                        "team:agent-integrations",
                        f"metrics_version:{METRIC_VERSION}",
                    ],
                )
            )

    configuration = Configuration()
    configuration.request_timeout = (5, 5)
    configuration.api_key = {
        "apiKeyAuth": config_file_info["api_key"],
    }
    configuration.server_variables["site"] = config_file_info["site"]

    # Format the sizes dictionary into a human-readable summary
    summary_lines = []

    for platform, py_versions in sizes._total_sizes.items():
        for py_version, size_bytes in py_versions.items():
            summary_lines.append(
                f"Platform: {platform}, Python: {py_version}, Size: "
                f"{convert_to_human_readable_size(size_bytes)} ({size_bytes} bytes)"
            )
    summary = "\n".join(summary_lines)

    total_metrics = len(metrics) + len(n_integrations_metrics) + len(n_dependencies_metrics)

    app.display(f"Sending {total_metrics} metrics to Datadog...")

    app.display("\nMetric summary:")
    app.display(summary)

    with ApiClient(configuration) as api_client:
        api_instance = MetricsApi(api_client)

        app.display_debug(f"Sending Metrics: {metrics}")
        api_instance.submit_metrics(body=MetricPayload(series=metrics))

        if mode is SizeMode.STATUS:
            app.display_debug(f"Sending N integrations metrics: {n_integrations_metrics}")
            api_instance.submit_metrics(body=MetricPayload(series=n_integrations_metrics))

            app.display_debug(f"Sending N dependencies metrics: {n_dependencies_metrics}")
            api_instance.submit_metrics(body=MetricPayload(series=n_dependencies_metrics))

    print("Metrics sent to Datadog")


@cache
def get_commit_data(commit: str | None = "") -> tuple[int, str, list[str], list[str]]:
    '''
    Get the commit data for a given commit. If no commit is provided, get the last commit data.
    '''
    cmd = ["git", "log", "-1", "--format=%s%n%ct"]
    cmd.append(commit) if commit else None
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    cmd_branch = ["git", "branch", "--remote", "--contains"]
    cmd_branch.append(commit) if commit else cmd_branch.append("HEAD")
    branch_name = subprocess.check_output(cmd_branch).decode("utf-8")
    ticket_pattern = r'\b(?:DBMON|SAASINT|AGENT|AI)-\d+\b'
    pr_pattern = r'#(\d+)'

    message, timestamp = result.stdout.strip().split('\n')
    tickets = list(set(re.findall(ticket_pattern, message) + re.findall(ticket_pattern, branch_name)))
    prs = re.findall(pr_pattern, message)
    if not tickets:
        tickets = [""]
    if not prs:
        prs = [""]
    return int(timestamp), message, tickets, prs


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
            List of commit SHAs (oldest to newest)
        """
        self._run("git fetch origin --quiet")
        self._run("git checkout origin/HEAD")
        try:
            if time:
                return self._run(f'git log --since="{time}" --reverse --pretty=format:%H -- {module_path}')
            elif not initial and not final:
                # Get all commits from first to latest
                return self._run(f"git log --reverse --pretty=format:%H -- {module_path}")
            elif not initial:
                # Get commits from first commit up to specified final commit
                return self._run(f"git log --reverse --pretty=format:%H ..{final} -- {module_path}")
            elif not final:
                # Get commits from specified initial commit up to latest
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


# Export format
def save_json(
    app: Application,
    file_path: str,
    modules: (list[CommitEntryWithDelta] | list[CommitEntryPlatformWithDelta]),
) -> None:
    if modules == []:
        return

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(modules, f, default=str, indent=2)
    app.display(f"JSON file saved to {file_path}")


def save_csv(
    app: Application,
    modules: list[CommitEntryWithDelta] | list[CommitEntryPlatformWithDelta],
    file_path: str,
) -> None:
    if modules == []:
        return

    headers = [k for k in modules[0].keys() if k not in ["Size", "Delta"]]

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(",".join(headers) + "\n")

        for row in modules:
            f.write(",".join(format(str(row.get(h, ""))) for h in headers) + "\n")

    app.display(f"CSV file saved to {file_path}")


def format(s: str) -> str:
    """
    Wraps the string in double quotes if it contains a comma, for safe CSV formatting.
    """
    return f'"{s}"' if "," in s else s


def save_markdown(
    app: Application,
    title: str,
    modules: list[CommitEntryWithDelta] | list[CommitEntryPlatformWithDelta],
    file_path: str,
) -> None:
    if modules == []:
        return

    headers = [k for k in modules[0].keys() if "Bytes" not in k]

    # Group modules by platform and version
    grouped_modules = {(modules[0].get("Platform", ""), modules[0].get("Python_Version", "")): [modules[0]]}
    for module in modules[1:]:
        platform = module.get("Platform", "")
        version = module.get("Python_Version", "")
        key = (platform, version)
        if key not in grouped_modules:
            grouped_modules[key] = []
        if any(str(value).strip() not in ("", "0", "0001-01-01") for value in module.values()):
            grouped_modules[key].append(module)

    lines = []
    lines.append(f"# {title}")
    lines.append("")

    for (platform, version), group in grouped_modules.items():
        if platform and version:
            lines.append(f"## Platform: {platform}, Python Version: {version}")

        lines.append("")
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for row in group:
            lines.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")
        lines.append("")

    markdown = "\n".join(lines)

    with open(file_path, "a", encoding="utf-8") as f:
        f.write(markdown)
    app.display(f"Markdown table saved to {file_path}")


def print_table(
    app: Application,
    mode: str,
    modules: list[CommitEntryWithDelta] | list[CommitEntryPlatformWithDelta],
) -> None:
    if modules == []:
        return

    columns = [col for col in modules[0].keys() if "Bytes" not in col]
    modules_table: dict[str, dict[int, str]] = {col: {} for col in columns}
    for i, row in enumerate(modules):
        if row.get("Size_Bytes") == 0:
            continue
        for key in columns:
            modules_table[key][i] = str(row.get(key, ""))

    app.display_table(mode, modules_table)
