import json
import os
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from ddev.cli.size.common import (
    compress,
    convert_to_human_readable_size,
    extract_version_from_about_py,
    format_modules,
    get_dependencies_list,
    get_dependencies_sizes,
    get_files,
    get_gitignore_files,
    get_valid_platforms,
    get_valid_versions,
    is_correct_dependency,
    is_valid_integration,
    print_csv,
    print_json,
)


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
        "macos-x86_64_3.12.txt",
        "macos-x86_64_py2.txt",
        "macos-x86_64_py3.txt",
        "windows-x86_64_3.12.txt",
        "windows-x86_64_py2.txt",
        "windows-x86_64_py3.txt",
    ]

    expected_platforms = {"linux-aarch64", "linux-x86_64", "macos-x86_64", "windows-x86_64"}
    with patch("os.listdir", return_value=filenames):
        platforms = get_valid_platforms("fake_repo")
        assert platforms == expected_platforms


def test_get_valid_versions():
    filenames = [
        "linux-aarch64_3.12.txt",
        "linux-aarch64_py2.txt",
        "linux-aarch64_py3.txt",
        "linux-x86_64_3.12.txt",
        "linux-x86_64_py2.txt",
        "linux-x86_64_py3.txt",
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


def test_is_correct_dependency():
    assert is_correct_dependency("windows-x86_64", "3.12", "windows-x86_64-3.12")
    assert not is_correct_dependency("windows-x86_64", "3.12", "linux-x86_64-3.12")
    assert not is_correct_dependency("windows-x86_64", "3.13", "windows-x86_64-3.12")


def test_convert_to_human_readable_size():
    assert convert_to_human_readable_size(500) == "500 B"
    assert convert_to_human_readable_size(1024) == "1.0 KB"
    assert convert_to_human_readable_size(1048576) == "1.0 MB"
    assert convert_to_human_readable_size(1073741824) == "1.0 GB"


def test_is_valid_integration():
    included_folder = "datadog_checks" + os.sep
    ignored_files = {"datadog_checks_dev", "datadog_checks_tests_helper"}
    git_ignore = [".git", "__pycache__"]

    assert is_valid_integration(to_native_path("datadog_checks/example.py"), included_folder, ignored_files, git_ignore)
    assert not is_valid_integration(to_native_path("__pycache__/file.py"), included_folder, ignored_files, git_ignore)
    assert not is_valid_integration(
        to_native_path("datadog_checks_dev/example.py"), included_folder, ignored_files, git_ignore
    )
    assert not is_valid_integration(to_native_path(".git/config"), included_folder, ignored_files, git_ignore)


def test_get_dependencies_list():
    file_content = "dependency1 @ https://example.com/dependency1-1.1.1-.whl\ndependency2 @ https://example.com/dependency2-1.1.1-.whl"
    mock_open_obj = mock_open(read_data=file_content)
    with patch("builtins.open", mock_open_obj):
        deps, urls, versions = get_dependencies_list("fake_path")
    assert deps == ["dependency1", "dependency2"]
    assert urls == ["https://example.com/dependency1-1.1.1-.whl", "https://example.com/dependency2-1.1.1-.whl"]
    assert versions == ["1.1.1", "1.1.1"]


def test_get_dependencies_sizes():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Length": "12345"}
    with patch("requests.head", return_value=mock_response):
        file_data = get_dependencies_sizes(["dependency1"], ["https://example.com/dependency1.whl"], ["1.1.1"], True)
    assert file_data == [
        {
            "Name": "dependency1",
            "Version": "1.1.1",
            "Size_Bytes": 12345,
            "Size": convert_to_human_readable_size(12345),
            "Type": "Dependency",
        }
    ]


def test_format_modules_multiple_platform():
    modules = [
        {"Name": "module1", "Type": "A", "Size_Bytes": 1500},
        {"Name": "module2", "Type": "B", "Size_Bytes": 3000},
    ]
    platform = "linux-aarch64"
    version = "3.12"

    expected_output = [
        {
            "Name": "module1",
            "Type": "A",
            "Size_Bytes": 1500,
            "Platform": "linux-aarch64",
            "Python_Version": "3.12",
        },
        {
            "Name": "module2",
            "Type": "B",
            "Size_Bytes": 3000,
            "Platform": "linux-aarch64",
            "Python_Version": "3.12",
        },
    ]

    assert format_modules(modules, platform, version, True) == expected_output


def test_format_modules_one_plat():
    modules = [
        {"Name": "module1", "Type": "A", "Size_Bytes": 1500},
        {"Name": "module2", "Type": "B", "Size_Bytes": 3000},
    ]
    platform = "linux-aarch64"
    version = "3.12"

    expected_output = [
        {
            "Name": "module1",
            "Type": "A",
            "Size_Bytes": 1500,
        },
        {
            "Name": "module2",
            "Type": "B",
            "Size_Bytes": 3000,
        },
    ]

    assert format_modules(modules, platform, version, False) == expected_output


def test_get_files_grouped_and_with_versions():
    repo_path = Path("fake_repo")

    os_walk_output = [
        (repo_path / "integration1" / "datadog_checks", [], ["__about__.py", "file2.py"]),
        (repo_path / "integration2" / "datadog_checks", [], ["__about__.py"]),
    ]

    def mock_is_valid_integration(path, included_folder, ignored, ignored_files):
        return True

    def mock_getsize(path):
        file_sizes = {
            repo_path / "integration1" / "datadog_checks" / "file2.py": 2000,
            repo_path / "integration1" / "datadog_checks" / "__about__.py": 1000,
            repo_path / "integration2" / "datadog_checks" / "__about__.py": 3000,
        }
        return file_sizes[Path(path)]

    with (
        patch("os.walk", return_value=[(str(p), dirs, files) for p, dirs, files in os_walk_output]),
        patch("os.path.getsize", side_effect=mock_getsize),
        patch("ddev.cli.size.common.get_gitignore_files", return_value=set()),
        patch("ddev.cli.size.common.is_valid_integration", side_effect=mock_is_valid_integration),
        patch("ddev.cli.size.common.extract_version_from_about_py", return_value="1.2.3"),
        patch("ddev.cli.size.common.convert_to_human_readable_size", side_effect=lambda s: f"{s / 1024:.2f} KB"),
    ):

        result = get_files(repo_path, compressed=False)

    expected = [
        {
            "Name": "integration1",
            "Version": "1.2.3",
            "Size_Bytes": 3000,
            "Size": "2.93 KB",
            "Type": "Integration",
        },
        {
            "Name": "integration2",
            "Version": "1.2.3",
            "Size_Bytes": 3000,
            "Size": "2.93 KB",
            "Type": "Integration",
        },
    ]

    assert result == expected


def test_get_gitignore_files():
    mock_gitignore = f"__pycache__{os.sep}\n*.log\n"  # Sample .gitignore file
    repo_path = "fake_repo"
    with patch("builtins.open", mock_open(read_data=mock_gitignore)):
        with patch("os.path.exists", return_value=True):
            ignored_patterns = get_gitignore_files(repo_path)
    assert ignored_patterns == ["__pycache__" + os.sep, "*.log"]


def test_compress():
    fake_content = b'a' * 16384
    original_size = len(fake_content)

    m = mock_open(read_data=fake_content)
    with patch("builtins.open", m):
        compressed_size = compress(to_native_path("fake/path/file.py"))

    assert isinstance(compressed_size, int)
    assert compressed_size > 0
    assert compressed_size < original_size


def test_print_csv():
    mock_app = MagicMock()
    modules = [
        {"Name": "module1", "Size B": 123, "Size": "2 B"},
        {"Name": "module,with,comma", "Size B": 456, "Size": "2 B"},
    ]

    print_csv(mock_app, modules=modules)

    expected_calls = [
        (("Name,Size B",),),
        (('module1,123',),),
        (('"module,with,comma",456',),),
    ]

    actual_calls = mock_app.display.call_args_list
    assert actual_calls == expected_calls


def test_print_json():
    mock_app = MagicMock()

    modules = [
        {"name": "mod1", "size": "100"},
        {"name": "mod2", "size": "200"},
        {"name": "mod3", "size": "300"},
    ]
    print_json(mock_app, modules)

    expected_calls = [
        (("[",),),
        (('{"name": "mod1", "size": "100"}',),),
        ((",",),),
        (('{"name": "mod2", "size": "200"}',),),
        ((",",),),
        (('{"name": "mod3", "size": "300"}',),),
        (("]",),),
    ]

    actual_calls = mock_app.display.call_args_list
    print(actual_calls)
    assert actual_calls == expected_calls

    result = "".join(call[0][0] for call in actual_calls)
    parsed = json.loads(result)
    assert parsed == [
        {"name": "mod1", "size": "100"},
        {"name": "mod2", "size": "200"},
        {"name": "mod3", "size": "300"},
    ]


def test_extract_version_from_about_py_pathlib():
    # Usa Path para compatibilidad multiplataforma
    fake_path = Path("some") / "module" / "__about__.py"
    fake_content = "__version__ = '1.2.3'\n"

    with patch("builtins.open", mock_open(read_data=fake_content)):
        version = extract_version_from_about_py(str(fake_path))

    assert version == "1.2.3"


def test_extract_version_from_about_py_no_version_pathlib():
    fake_path = Path("another") / "module" / "__about__.py"
    fake_content = "version = 'not_defined'\n"

    with patch("builtins.open", mock_open(read_data=fake_content)):
        version = extract_version_from_about_py(str(fake_path))

    assert version == ""
