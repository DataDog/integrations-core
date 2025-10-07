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
from functools import cache
from types import TracebackType
from typing import TYPE_CHECKING, Optional, Type, TypedDict, overload

import requests
import squarify
from typing_extensions import Literal, NotRequired

from ddev.cli.application import Application
from ddev.utils.fs import Path
from ddev.utils.toml import load_toml_file

METRIC_VERSION = -1

RESOLVE_BUILD_DEPS_WORKFLOW = '.github/workflows/resolve-build-deps.yaml'
MEASURE_DISK_USAGE_WORKFLOW = '.github/workflows/measure-disk-usage.yml'

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.patches import Patch


class FileDataEntry(TypedDict):
    Name: str  # Integration/Dependency name
    Version: str  # Version of the Integration/Dependency
    Size_Bytes: int  # Size in bytes
    Size: str  # Human-readable size
    Type: str  # Integration/Dependency
    Platform: str  # Target platform (e.g. linux-aarch64)
    Python_Version: str  # Target Python version (e.g. 3.12)
    Delta_Type: NotRequired[str]  # Change type (New, Removed, Modified)
    Percentage: NotRequired[float]  # Percentage of the size change


class DependencyEntry(TypedDict):
    compressed: NotRequired[int]  # Size in bytes
    uncompressed: NotRequired[int]  # Size in bytes
    Version: str  # Version of the Dependency


class DeltaTypeGroup(TypedDict):
    Modules: list[FileDataEntry]
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
    platform: str  # Target platform for analysis (e.g. linux-aarch64)
    py_version: str  # Target Python version for analysis
    compressed: bool  # Whether to analyze compressed file sizes
    format: Optional[list[str]]  # Output format options (png, csv, markdown, json)
    show_gui: bool  # Whether to display interactive visualization


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


def is_correct_dependency(platform: str, version: str, name: str) -> bool:
    # The name of the dependency file is in the format of {platform}_{version}.txt e.g. linux-aarch64_3.12.txt
    _platform, _version = name.rsplit(".", 1)[0].rsplit("_", 1)
    return platform == _platform and version == _version


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


def convert_to_human_readable_size(size_bytes: float) -> str:
    for unit in [" B", " KiB", " MiB", " GiB"]:
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


def get_files(repo_path: str | Path, compressed: bool, py_version: str, platform: str) -> list[FileDataEntry]:
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

    return [
        {
            "Name": name,
            "Version": integration_versions.get(name, ""),
            "Size_Bytes": size,
            "Size": convert_to_human_readable_size(size),
            "Type": "Integration",
            "Platform": platform,
            "Python_Version": py_version,
        }
        for name, size in integration_sizes.items()
    ]


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


def get_dependencies(repo_path: str | Path, platform: str, py_version: str, compressed: bool) -> list[FileDataEntry]:
    """
    Gets the list of dependencies for a given platform and Python version and returns a FileDataEntry that includes:
    Name, Version, Size_Bytes, Size, and Type.
    """
    resolved_path = os.path.join(repo_path, ".deps", "resolved")

    for filename in os.listdir(resolved_path):
        file_path = os.path.join(resolved_path, filename)

        if os.path.isfile(file_path) and is_correct_dependency(platform, py_version, filename):
            deps, download_urls, versions = get_dependencies_list(file_path)
            return get_dependencies_sizes(deps, download_urls, versions, compressed, platform, py_version)
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
            {
                "Name": str(dep),
                "Version": version,
                "Size_Bytes": int(size),
                "Size": convert_to_human_readable_size(size),
                "Type": "Dependency",
                "Platform": platform,
                "Python_Version": py_version,
            }
        )

    return file_data


def get_dependencies_from_json(
    dependency_sizes: Path, platform: str, py_version: str, compressed: bool
) -> list[FileDataEntry]:
    data = json.loads(dependency_sizes.read_text())
    size_key = "compressed" if compressed else "uncompressed"
    return [
        {
            "Name": name,
            "Version": sizes.get("version", ""),
            "Size_Bytes": int(sizes.get(size_key, 0)),
            "Size": convert_to_human_readable_size(sizes.get(size_key, 0)),
            "Type": "Dependency",
            "Platform": platform,
            "Python_Version": py_version,
        }
        for name, sizes in data.items()
    ]


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


def save_json(
    app: Application,
    file_path: str,
    modules: (list[FileDataEntry] | list[CommitEntryWithDelta] | list[CommitEntryPlatformWithDelta]),
) -> None:
    if modules == []:
        return

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(modules, f, default=str, indent=2)
    app.display(f"JSON file saved to {file_path}")


def save_csv(
    app: Application,
    modules: list[FileDataEntry] | list[CommitEntryWithDelta] | list[CommitEntryPlatformWithDelta],
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
    modules: list[FileDataEntry] | list[CommitEntryWithDelta] | list[CommitEntryPlatformWithDelta],
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
        elif platform:
            lines.append(f"## Platform: {platform}")
        elif version:
            lines.append(f"## Python Version: {version}")
        else:
            lines.append("## Other")

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
    modules: list[FileDataEntry] | list[CommitEntryWithDelta] | list[CommitEntryPlatformWithDelta],
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


def save_quality_gate_html(
    app: Application,
    modules: list[FileDataEntry],
    file_path: str,
    old_commit: str,
    threshold_percentage: int,
    old_size: dict[tuple[str, str], int],
    total_diff: dict[tuple[str, str], int],
    passes_quality_gate: bool,
) -> None:
    """
    Saves the modules list to HTML format, if the ouput is larger than the PR comment size max,
    it ouputs the short version.
    """
    if modules == []:
        return

    html = str()

    groups = group_modules(modules)
    html_headers = get_html_headers(threshold_percentage, old_commit, passes_quality_gate)
    for (platform, py_version), delta_type_groups in groups.items():
        html_subheaders = str()

        sign_total = "+" if total_diff[(platform, py_version)] > 0 else ""
        threshold = convert_to_human_readable_size(old_size[(platform, py_version)] * threshold_percentage)

        html_subheaders += f"<details><summary><h4>Size Delta for {platform} and Python {py_version}:\n"
        html_subheaders += (
            f"{sign_total}{convert_to_human_readable_size(total_diff[(platform, py_version)])} "
            f"(Threshold: {threshold})</h4></summary>\n\n"
        )

        tables = str()

        tables += append_html_entry(delta_type_groups["New"], "Added")
        tables += append_html_entry(delta_type_groups["Removed"], "Removed")
        tables += append_html_entry(delta_type_groups["Modified"], "Modified")

        close_details = "</details>\n\n"

        html += f"{html_subheaders}\n{tables}\n{close_details}"

    html = f"{html_headers}\n{html}"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html)
    app.display(f"HTML file saved to {file_path}")


def save_quality_gate_html_table(
    app: Application,
    modules: list[FileDataEntry],
    file_path: str,
    old_commit: str,
    threshold_percentage: int,
    old_size: dict[tuple[str, str], int],
    total_diff: dict[tuple[str, str], int],
) -> None:
    html_headers = get_html_headers(threshold_percentage, old_commit, False)

    table_rows = []
    groups = group_modules(modules)
    # Order the groups by platform and python version
    for (platform, py_version), delta_type_groups in sorted(groups.items(), key=lambda x: (x[0][0], x[0][1])):
        diff = total_diff.get((platform, py_version), 0)
        sign_total = "+" if diff > 0 else ""
        delta_compressed_size = f"{sign_total}{convert_to_human_readable_size(diff)}"

        threshold_bytes = old_size.get((platform, py_version), 0) * threshold_percentage / 100
        threshold = f"{convert_to_human_readable_size(threshold_bytes)}"

        sign_added = "+" if delta_type_groups["New"]["Total"] > 0 else ""
        sign_removed = "+" if delta_type_groups["Removed"]["Total"] > 0 else ""
        sign_modified = "+" if delta_type_groups["Modified"]["Total"] > 0 else ""

        total_added = f"{sign_added}{convert_to_human_readable_size(delta_type_groups['New']['Total'])}"
        total_removed = f"{sign_removed}{convert_to_human_readable_size(delta_type_groups['Removed']['Total'])}"
        total_modified = f"{sign_modified}{convert_to_human_readable_size(delta_type_groups['Modified']['Total'])}"

        status = "❌" if diff >= threshold_bytes else "✅"

        table_rows.append(
            "<tr>"
            f"<td>{platform}</td>"
            f"<td>{py_version}</td>"
            f"<td>{total_added}</td>"
            f"<td>{total_removed}</td>"
            f"<td>{total_modified}</td>"
            f"<td>{delta_compressed_size}</td>"
            f"<td>{threshold}</td>"
            f"<td>{status}</td>"
            "</tr>"
        )

    html_table = (
        "<table>\n"
        "  <thead>\n"
        "    <tr>\n"
        "      <th>Platform</th>\n"
        "      <th>Python</th>\n"
        "      <th>&Delta; Added</th>\n"
        "      <th>&Delta; Removed</th>\n"
        "      <th>&Delta; Modified</th>\n"
        "      <th>&Delta; Total</th>\n"
        "      <th>Threshold</th>\n"
        "      <th>Status</th>\n"
        "    </tr>\n"
        "  </thead>\n"
        "  <tbody>\n"
        f"{''.join(table_rows)}\n"
        "  </tbody>\n"
        "</table>"
    )

    final_html = f"{html_headers}\n{html_table}"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(final_html)

    app.display(f"HTML file saved to {file_path}")


def get_html_headers(threshold_percentage: int, old_commit: str, passes_quality_gate: bool) -> str:
    html_headers = (
        "<h2>⛔ Size Quality Gates Not Passed</h2>"
        if not passes_quality_gate
        else "<h2>✅ Size Quality Gates Passed</h2>"
    )
    html_headers += (
        "<p>"
        f"<strong>Threshold:</strong> {threshold_percentage}% per platform and Python version<br>"
        "<strong>Compared to commit:</strong> "
        f'<a href="https://github.com/DataDog/integrations-core/commit/{old_commit}">{old_commit[:7]}</a>'
        "</p>"
        "<h3>Compressed Size Changes</h3>"
    )

    return html_headers


def group_modules(
    modules: list[FileDataEntry],
) -> dict[tuple[str, str], dict[str, DeltaTypeGroup]]:
    groups: dict[tuple[str, str], dict[str, DeltaTypeGroup]] = {}

    for m in modules:
        platform_key = (m.get("Platform", ""), m.get("Python_Version", ""))
        delta_type = m.get("Delta_Type", "")

        if platform_key not in groups:
            groups[platform_key] = {
                "New": {"Modules": [], "Total": 0},
                "Removed": {"Modules": [], "Total": 0},
                "Modified": {"Modules": [], "Total": 0},
            }

        if delta_type in groups[platform_key]:
            groups[platform_key][delta_type]["Modules"].append(m)
            groups[platform_key][delta_type]["Total"] += m.get("Size_Bytes", 0)

    return groups


def append_html_entry(delta_type_group: DeltaTypeGroup, type: str) -> str:
    html = str()
    if delta_type_group["Total"] != 0:
        sign = "+" if delta_type_group["Total"] > 0 else ""
        html += (
            f"<b>{type}:</b> {len(delta_type_group['Modules'])} item(s), {sign}"
            f"{convert_to_human_readable_size(delta_type_group['Total'])}\n"
        )
        html += "<table><tr><th>Type</th><th>Name</th><th>Version</th><th>Size Delta</th><th>Percentage</th></tr>\n"
        for e in delta_type_group["Modules"]:
            html += f"<tr><td>{e.get('Type', '')}</td><td>{e.get('Name', '')}</td><td>{e.get('Version', '')}</td>"
            html += f"<td>{e.get('Size', '')}</td><td>{e.get('Percentage', '')}%</td></tr>\n"
        html += "</table>\n"
    else:
        html += f"No {type.lower()} dependencies/integrations\n\n"

    return html


def export_format(
    app: Application,
    format: list[str],
    modules: list[FileDataEntry],
    mode: Literal["status", "diff"],
    platform: str | None,
    py_version: str | None,
    compressed: bool,
) -> None:
    size_type = "compressed" if compressed else "uncompressed"
    name = f"{mode}_{size_type}"
    if platform:
        name += f"_{platform}"
    if py_version:
        name += f"_{py_version}"
    for output_format in format:
        if output_format == "csv":
            csv_filename = f"{name}.csv"
            save_csv(app, modules, csv_filename)

        elif output_format == "json":
            json_filename = f"{name}.json"
            save_json(app, json_filename, modules)

        elif output_format == "markdown":
            markdown_filename = f"{name}.md"
            save_markdown(app, "Status", modules, markdown_filename)


def plot_treemap(
    app: Application,
    modules: list[FileDataEntry],
    title: str,
    show: bool,
    mode: Literal["status", "diff"],
    path: Optional[str] = None,
) -> None:
    import matplotlib.pyplot as plt

    if modules == []:
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

    if path:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        plt.savefig(path, bbox_inches="tight", format="png")
        app.display(f"Treemap saved to {path}")
    if show:
        plt.show()


def plot_status_treemap(
    modules: list[FileDataEntry] | list[FileDataEntry],
) -> tuple[list[dict[str, float]], list[tuple[float, float, float, float]], list[Patch]]:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    # Calculate the area of the rectangles
    sizes = [mod["Size_Bytes"] for mod in modules]
    norm_sizes = squarify.normalize_sizes(sizes, 100, 100)
    rects = squarify.squarify(norm_sizes, 0, 0, 100, 100)

    # Define the colors for each type
    cmap_int = plt.get_cmap("Purples")
    cmap_dep = plt.get_cmap("Reds")

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
        Patch(color=plt.get_cmap("Purples")(0.6), label="Integration"),
        Patch(color=plt.get_cmap("Reds")(0.6), label="Dependency"),
    ]
    return rects, colors, legend_handles


def plot_diff_treemap(
    modules: list[FileDataEntry] | list[FileDataEntry],
) -> tuple[list[dict[str, float]], list[tuple[float, float, float, float]], list[Patch]]:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    # Define the colors for each type
    cmap_pos = plt.get_cmap("Oranges")
    cmap_neg = plt.get_cmap("Blues")

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
    modules: list[FileDataEntry] | list[FileDataEntry],
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
    for rect, mod, color in zip(rects, modules, colors, strict=False):
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


def send_metrics_to_dd(
    app: Application,
    modules: list[FileDataEntry],
    org: str | None,
    key: str | None,
    site: str | None,
    compressed: bool,
    mode: Literal["status", "diff"],
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

    for item in modules:
        delta_type = item.get('Delta_Type', '')
        metrics.append(
            MetricSeries(
                metric=f"{metric_name}.size_{mode}",
                type=gauge_type,
                points=[MetricPoint(timestamp=timestamp, value=item["Size_Bytes"])],
                tags=[
                    f"module_name:{item['Name']}",
                    f"module_type:{item['Type']}",
                    f"name_type:{item['Type']}({item['Name']})",
                    f"python_version:{item['Python_Version']}",
                    f"module_version:{item['Version']}",
                    f"platform:{item['Platform']}",
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
        if mode == "status":
            key_count = (item['Platform'], item['Python_Version'])
            if key_count not in n_integrations:
                n_integrations[key_count] = 0
            if key_count not in n_dependencies:
                n_dependencies[key_count] = 0
            if item['Type'] == 'Integration':
                n_integrations[key_count] += 1
            elif item['Type'] == 'Dependency':
                n_dependencies[key_count] += 1

    if mode == "status":
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

    with ApiClient(configuration) as api_client:
        api_instance = MetricsApi(api_client)
        api_instance.submit_metrics(body=MetricPayload(series=metrics))
        if mode == "status":
            api_instance.submit_metrics(body=MetricPayload(series=n_integrations_metrics))
            api_instance.submit_metrics(body=MetricPayload(series=n_dependencies_metrics))
    print("Metrics sent to Datadog")


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


@cache
def get_last_dependency_sizes_artifact(
    app: Application, commit: str, platform: str, py_version: str, compressed: bool
) -> Path | None:
    '''
    Lockfiles of dependencies are not updated in the same commit as the dependencies are updated.
    So in each commit, there is an artifact with the sizes of the wheels that were built to get the actual
    size of that commit.
    '''
    dep_sizes_json = get_dep_sizes_json(commit, platform, py_version)
    if not dep_sizes_json:
        base_commit = app.repo.git.merge_base(commit, "origin/master")
        if base_commit != commit:
            previous_commit = base_commit
        else:
            previous_commit = app.repo.git.log(["hash:%H"], n=2, source=commit)[1]["hash"]

        dep_sizes_json = get_status_sizes_from_commit(
            app, previous_commit, platform, py_version, compressed, file=True, only_dependencies=True
        )
    return Path(dep_sizes_json) if dep_sizes_json else None


@cache
def get_dep_sizes_json(current_commit: str, platform: str, py_version: str) -> Path | None:
    '''
    Gets the dependency sizes json for a given commit and platform when dependencies were resolved.
    '''
    print(f"Getting dependency sizes json for commit: {current_commit}, platform: {platform}, py_version: {py_version}")
    run_id = get_run_id(current_commit, RESOLVE_BUILD_DEPS_WORKFLOW)
    if run_id:
        return get_current_sizes_json(run_id, platform, py_version)
    else:
        return None


@cache
def get_run_id(commit: str, workflow: str) -> str | None:
    print(f"Getting run id for commit: {commit}, workflow: {workflow}")

    result = subprocess.run(
        [
            'gh',
            'run',
            'list',
            '--workflow',
            workflow,
            '-c',
            commit,
            '--json',
            'databaseId',
            '--jq',
            '.[-1].databaseId',
        ],
        capture_output=True,
        text=True,
    )

    run_id = result.stdout.strip() if result.stdout else None
    if run_id:
        print(f"Run id: {run_id}")
    else:
        print(f"No run id found for commit: {commit}, workflow: {workflow}")

    return run_id


@cache
def get_current_sizes_json(run_id: str, platform: str, py_version: str) -> Path | None:
    '''
    Downloads the dependency sizes json for a given run id and platform when dependencies were resolved.
    '''
    print(f"Getting current sizes json for run_id={run_id}, platform={platform}")
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Downloading artifacts to {tmpdir}")
        try:
            subprocess.run(
                [
                    'gh',
                    'run',
                    'download',
                    run_id,
                    '--name',
                    f'target-{platform}',
                    '--dir',
                    tmpdir,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            if e.stderr and "no artifact matches any of the names or patterns provided" in e.stderr:
                print(f"No artifact found for run_id={run_id}, platform={platform}")
            else:
                print(f"Failed to download current sizes json: {e}")

            print("Comparing to merge base commit")
            return None

        print(f"Downloaded artifacts to {tmpdir}")
        sizes_file = Path(tmpdir) / platform / 'py3' / 'sizes.json'

        if not sizes_file.is_file():
            print(f"Sizes artifact not found at {sizes_file}")
            return None

        print(f"Found sizes artifact at {sizes_file}")
        dest_path = sizes_file.rename(f"{platform}_{py_version}.json")
        return dest_path


@cache
def get_artifact(run_id: str, artifact_name: str, target_dir: str | None = None) -> Path | None:
    print(f"Downloading artifact: {artifact_name} from run_id={run_id}")
    try:
        cmd = [
            'gh',
            'run',
            'download',
            run_id,
            '--name',
            artifact_name,
        ]
        if target_dir:
            cmd.extend(['--dir', target_dir])

        subprocess.run(cmd, check=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to download artifact: {artifact_name} from run_id={run_id}: {e}")
        return None

    artifact_path = Path(target_dir) / artifact_name if target_dir else Path(artifact_name)
    print(f"Artifact downloaded to: {artifact_path}")
    return artifact_path


@overload
def get_status_sizes_from_commit(
    app: Application,
    commit: str,
    platform: str,
    py_version: str,
    compressed: bool,
    file: Literal[True],
    only_dependencies: bool,
) -> Path | None: ...


@overload
def get_status_sizes_from_commit(
    app: Application,
    commit: str,
    platform: str,
    py_version: str,
    compressed: bool,
    file: Literal[False],
    only_dependencies: Literal[False],
) -> list[FileDataEntry]: ...


@overload
def get_status_sizes_from_commit(
    app: Application,
    commit: str,
    platform: str,
    py_version: str,
    compressed: bool,
    file: Literal[False],
    only_dependencies: Literal[True],
) -> dict[str, DependencyEntry]: ...


@cache
def get_status_sizes_from_commit(
    app: Application,
    commit: str,
    platform: str,
    py_version: str,
    compressed: bool,
    file: bool = False,
    only_dependencies: bool = False,
) -> list[FileDataEntry] | dict[str, DependencyEntry] | Path | None:
    '''
    Gets the sizes json for a given commit from the measure disk usage workflow.
    '''
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Getting sizes json for {commit=}")

        if (run_id := get_run_id(commit, MEASURE_DISK_USAGE_WORKFLOW)) is None:
            return []

        artifact_name = 'status_compressed.json' if compressed else 'status_uncompressed.json'
        sizes_json = get_artifact(run_id, artifact_name, tmpdir)

        if not sizes_json:
            app.display_error(f"Sizes not found for {commit=}")
            return []

        print(f"Sizes json: {sizes_json}")
        sizes: list[FileDataEntry] | dict[str, DependencyEntry]
        if only_dependencies:
            sizes = parse_dep_sizes_json(sizes_json, platform, py_version, compressed)
        else:
            sizes = filter_sizes_json(sizes_json, platform, py_version)

        if file and sizes:
            target_path = f"{platform}_{py_version}.json"
            with open(target_path, "w") as f:
                json.dump(sizes, f, indent=2)
            return Path(target_path)
        elif file and not sizes:
            return None
        else:
            return sizes


def filter_sizes_json(sizes_json: Path, platform: str, py_version: str) -> list[FileDataEntry]:
    '''
    Filters the sizes json for a given platform and python version.
    '''
    sizes_list: list[FileDataEntry] = list(json.loads(sizes_json.read_text()))
    return [size for size in sizes_list if size["Platform"] == platform and size["Python_Version"] == py_version]


@cache
def parse_dep_sizes_json(
    sizes_json_path: Path,
    platform: str,
    py_version: str,
    compressed: bool,
) -> dict[str, DependencyEntry]:
    '''
    Parses the dependency sizes json for a given platform and python version.
    '''
    sizes_list = list(json.loads(sizes_json_path.read_text()))
    sizes: dict[str, DependencyEntry] = {}
    for dep in sizes_list:
        if (
            dep.get("Type") == "Dependency"
            and dep.get("Platform") == platform
            and dep.get("Python_Version") == py_version
        ):
            name = dep["Name"]
            entry: DependencyEntry = {"Version": dep.get("Version", "")}
            if compressed:
                entry["compressed"] = int(dep["Size_Bytes"])
            else:
                entry["uncompressed"] = int(dep["Size_Bytes"])
            sizes[name] = entry
    return sizes


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
