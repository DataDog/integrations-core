import io
import os
import zipfile
from unittest.mock import MagicMock, mock_open, patch

import pytest

from ddev.cli.size.utils.common_funcs import (
    check_python_version,
    compress,
    extract_version_from_about_py,
    get_dependencies_from_artifact,
    get_dependencies_list,
    get_dependencies_sizes,
    get_files,
    get_gitignore_files,
    get_valid_platforms,
    get_valid_versions,
    is_correct_dependency,
    is_valid_integration_file,
)
from ddev.cli.size.utils.size_model import Size, Sizes
from ddev.utils.fs import Path


def to_native_path(path: str) -> str:
    return path.replace("/", os.sep)


def test_get_valid_platforms():
    filenames = [
        "linux-aarch64_3.12.txt",
        "linux-aarch64_py2.txt",
        "linux-aarch64_py3.txt",
        "linux-x86_64_3.12.txt",
        "linux-x86_64_py2.txt",
        "linux-x86_64_py3.txt",
        "macos-aarch64_3.12.txt",
        "macos-aarch64_py2.txt",
        "macos-aarch64_py3.txt",
        "macos-x86_64_3.12.txt",
        "macos-x86_64_py2.txt",
        "macos-x86_64_py3.txt",
        "windows-x86_64_3.12.txt",
        "windows-x86_64_py2.txt",
        "windows-x86_64_py3.txt",
    ]

    expected_platforms = {"linux-aarch64", "linux-x86_64", "macos-aarch64", "macos-x86_64", "windows-x86_64"}
    with patch("os.listdir", return_value=filenames):
        platforms = get_valid_platforms("fake_repo", {"3.12"})
        assert platforms == expected_platforms


def test_get_valid_versions():
    filenames = [
        "linux-aarch64_3.12.txt",
        "linux-aarch64_py2.txt",
        "linux-aarch64_py3.txt",
        "linux-x86_64_3.12.txt",
        "linux-x86_64_py2.txt",
        "linux-x86_64_py3.txt",
        "macos-aarch64_3.12.txt",
        "macos-aarch64_py2.txt",
        "macos-aarch64_py3.txt",
        "macos-x86_64_3.12.txt",
        "macos-x86_64_py2.txt",
        "macos-x86_64_py3.txt",
        "windows-x86_64_3.12.txt",
        "windows-x86_64_py2.txt",
        "windows-x86_64_py3.txt",
    ]

    expected_versions = {"3.12"}
    with patch("os.listdir", return_value=filenames):
        versions = get_valid_versions("fake_repo")
        assert versions == expected_versions


@pytest.mark.parametrize(
    "platform, version, dependency_file_name, expected",
    [
        pytest.param("windows-x86_64", "3.12", "windows-x86_64_3.12.txt", True, id="correct"),
        pytest.param("windows-x86_64", "3.12", "linux-x86_64_3.12.txt", False, id="incorrect_platform"),
        pytest.param("windows-x86_64", "3.13", "windows-x86_64_3.12.txt", False, id="incorrect_version"),
    ],
)
def test_is_correct_dependency(platform: str, version: str, dependency_file_name: str, expected: bool):
    assert is_correct_dependency(platform, version, dependency_file_name) is expected


@pytest.mark.parametrize(
    "file_path, expected",
    [
        pytest.param("datadog_checks/example.py", True, id="valid"),
        pytest.param("__pycache__/file.py", False, id="pycache"),
        pytest.param("datadog_checks_dev/example.py", False, id="checks_dev"),
        pytest.param(".git/config", False, id="git"),
    ],
)
def test_is_valid_integration_file(file_path, expected):
    repo_path = "fake_repo"
    with patch("ddev.cli.size.utils.common_funcs.get_gitignore_files", return_value=set()):
        assert is_valid_integration_file(to_native_path(file_path), repo_path) is expected


def test_get_dependencies_list(tmp_path: Path):
    file_content = "dependency1 @ https://example.com/dependency1/dependency1-1.1.1-.whl\ndependency2 @ https://example.com/dependency2/dependency2-1.1.1-.whl"
    file_path = tmp_path / "dependencies.txt"
    file_path.write_text(file_content)
    deps, urls, versions = get_dependencies_list(file_path)
    assert deps == ["dependency1", "dependency2"]
    assert urls == [
        "https://example.com/dependency1/dependency1-1.1.1-.whl",
        "https://example.com/dependency2/dependency2-1.1.1-.whl",
    ]
    assert versions == ["1.1.1", "1.1.1"]


def test_get_dependencies_sizes():
    # Create a valid zip file in memory
    fake_zip_bytes = io.BytesIO()
    with zipfile.ZipFile(fake_zip_bytes, 'w') as zf:
        zf.writestr('dummy.txt', 'hello world')
    fake_zip_bytes.seek(0)
    zip_content = fake_zip_bytes.read()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Length": "12345"}
    mock_response.content = zip_content
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = None
    with patch("requests.get", return_value=mock_response):
        file_data = get_dependencies_sizes(
            ["dependency1"],
            ["https://example.com/dependency1/dependency1-1.1.1-.whl"],
            ["1.1.1"],
            True,
            "linux-x86_64",
            "3.12",
        )

    assert file_data == Sizes(
        [
            Size(
                name="dependency1",
                version="1.1.1",
                size_bytes=11,
                type="Dependency",
                platform="linux-x86_64",
                python_version="3.12",
            )
        ]
    )


def test_get_files_grouped_and_with_versions():
    repo_path = Path("fake_repo")

    os_walk_output = [
        (repo_path / "integration1" / "datadog_checks", [], ["__about__.py", "file2.py"]),
        (repo_path / "integration2" / "datadog_checks", [], ["__about__.py"]),
    ]

    def mock_is_valid_integration_file(path, repo_path):
        return True

    def mock_getsize(path):
        file_sizes = {
            repo_path / "integration1" / "datadog_checks" / "file2.py": 2000,
            repo_path / "integration1" / "datadog_checks" / "__about__.py": 1000,
            repo_path / "integration2" / "datadog_checks" / "__about__.py": 3000,
        }
        return file_sizes[Path(path)]

    with (
        patch(
            "ddev.cli.size.utils.common_funcs.os.walk",
            return_value=[(str(p), dirs, files) for p, dirs, files in os_walk_output],
        ),
        patch("ddev.cli.size.utils.common_funcs.os.path.getsize", side_effect=mock_getsize),
        patch("ddev.cli.size.utils.common_funcs.get_gitignore_files", return_value=set()),
        patch("ddev.cli.size.utils.common_funcs.is_valid_integration_file", side_effect=mock_is_valid_integration_file),
        patch("ddev.cli.size.utils.common_funcs.extract_version_from_about_py", return_value="1.2.3"),
        patch(
            "ddev.cli.size.utils.common_funcs.convert_to_human_readable_size",
            side_effect=lambda s: f"{s / 1024:.2f} KB",
        ),
        patch("ddev.cli.size.utils.common_funcs.check_python_version", return_value=True),
    ):
        result = get_files(repo_path, compressed=False, py_version="3.12", platform="linux-x86_64")

    expected = Sizes(
        [
            Size(
                name="integration1",
                version="1.2.3",
                size_bytes=3000,
                type="Integration",
                platform="linux-x86_64",
                python_version="3.12",
            ),
            Size(
                name="integration2",
                version="1.2.3",
                size_bytes=3000,
                type="Integration",
                platform="linux-x86_64",
                python_version="3.12",
            ),
        ]
    )

    assert result == expected


@pytest.mark.parametrize(
    "py_version, expected",
    [
        pytest.param("3", True, id="py3"),
        pytest.param("2", False, id="py2"),
    ],
)
def test_check_version(py_version, expected):
    with (
        patch(
            "ddev.cli.size.utils.common_funcs.load_toml_file",
            return_value={"project": {"classifiers": ["Programming Language :: Python :: 3.12"]}},
        ),
        patch("ddev.cli.size.utils.common_funcs.os.path.exists", return_value=True),
    ):
        assert check_python_version("fake_repo", "integration1", py_version) is expected


def test_get_gitignore_files():
    mock_gitignore = f"__pycache__{os.sep}\n*.log\n"  # Sample .gitignore file
    repo_path = "fake_repo"
    with patch("builtins.open", mock_open(read_data=mock_gitignore)):
        with patch("ddev.cli.size.utils.common_funcs.os.path.exists", return_value=True):
            ignored_patterns = get_gitignore_files(repo_path)
    assert ignored_patterns == ["__pycache__" + os.sep, "*.log"]


def test_compress():
    fake_content = b"a" * 16384
    original_size = len(fake_content)

    m = mock_open(read_data=fake_content)
    with patch("builtins.open", m):
        compressed_size = compress(to_native_path("fake/path/file.py"))

    assert isinstance(compressed_size, int)
    assert compressed_size > 0
    assert compressed_size < original_size


@pytest.mark.parametrize(
    "file_content, expected_version",
    [
        pytest.param("__version__ = '1.2.3'", "1.2.3", id="version_present"),
        pytest.param("not_version = 'not_defined'", "", id="version_not_present"),
    ],
)
def test_extract_version_from_about_py(file_content: str, expected_version: str):
    fake_path = Path("some") / "module" / "__about__.py"
    with patch("ddev.cli.size.utils.common_funcs.open", mock_open(read_data=file_content)):
        version = extract_version_from_about_py(str(fake_path))
    assert version == expected_version


def test_get_dependencies_from_artifact():
    dep_size_dict = {
        "dep1": {"compressed": 1, "uncompressed": 2, "version": "1.1.1"},
        "dep2": {"compressed": 10, "uncompressed": 20, "version": "1.1.1"},
    }
    expected = Sizes(
        [
            Size(
                name="dep1",
                version="1.1.1",
                size_bytes=1,
                type="Dependency",
                platform="linux-x86_64",
                python_version="3.12",
            ),
            Size(
                name="dep2",
                version="1.1.1",
                size_bytes=10,
                type="Dependency",
                platform="linux-x86_64",
                python_version="3.12",
            ),
        ]
    )

    result = get_dependencies_from_artifact(dep_size_dict, "linux-x86_64", "3.12", True)
    assert result == expected
