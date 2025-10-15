import json
import os
import re
import tempfile
import zipfile

import requests

from ddev.cli.size.utils.general import convert_to_human_readable_size
from ddev.cli.size.utils.models import FileDataEntry, WrongDependencyFormat
from ddev.utils.fs import Path


def is_correct_dependency(platform: str, version: str, name: str) -> bool:
    # The name of the dependency file is in the format of {platform}_{version}.txt e.g. linux-aarch64_3.12.txt
    _platform, _version = name.rsplit(".", 1)[0].rsplit("_", 1)
    return platform == _platform and version == _version


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
