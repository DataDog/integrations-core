import os
import re
import zlib

from ddev.cli.size.utils.models import FileDataEntry
from ddev.utils.fs import Path
from ddev.utils.toml import load_toml_file


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
