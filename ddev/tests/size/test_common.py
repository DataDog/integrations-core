import io
import json
import os
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

from ddev.cli.size.utils.common_funcs import (
    check_python_version,
    compress,
    convert_to_human_readable_size,
    extract_version_from_about_py,
    format_modules,
    get_dependencies_list,
    get_dependencies_sizes,
    get_files,
    get_gitignore_files,
    get_org,
    get_valid_platforms,
    get_valid_versions,
    is_correct_dependency,
    is_valid_integration_file,
    save_csv,
    save_json,
    save_markdown,
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


def test_is_correct_dependency():
    assert is_correct_dependency("windows-x86_64", "3.12", "windows-x86_64-3.12")
    assert not is_correct_dependency("windows-x86_64", "3.12", "linux-x86_64-3.12")
    assert not is_correct_dependency("windows-x86_64", "3.13", "windows-x86_64-3.12")


def test_convert_to_human_readable_size():
    assert convert_to_human_readable_size(500) == "500 B"
    assert convert_to_human_readable_size(1024) == "1.0 KB"
    assert convert_to_human_readable_size(1048576) == "1.0 MB"
    assert convert_to_human_readable_size(1073741824) == "1.0 GB"


def test_is_valid_integration_file():
    repo_path = "fake_repo"
    with patch("ddev.cli.size.utils.common_funcs.get_gitignore_files", return_value=set()):
        assert is_valid_integration_file(to_native_path("datadog_checks/example.py"), repo_path)
        assert not is_valid_integration_file(to_native_path("__pycache__/file.py"), repo_path)
        assert not is_valid_integration_file(to_native_path("datadog_checks_dev/example.py"), repo_path)
        assert not is_valid_integration_file(to_native_path(".git/config"), repo_path)


def test_get_dependencies_list():
    file_content = "dependency1 @ https://example.com/dependency1/dependency1-1.1.1-.whl\ndependency2 @ https://example.com/dependency2/dependency2-1.1.1-.whl"
    mock_open_obj = mock_open(read_data=file_content)
    with patch("builtins.open", mock_open_obj):
        deps, urls, versions = get_dependencies_list("fake_path")
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
            ["dependency1"], ["https://example.com/dependency1/dependency1-1.1.1-.whl"], ["1.1.1"], True
        )

    assert file_data == [
        {
            "Name": "dependency1",
            "Version": "1.1.1",
            "Size_Bytes": 11,
            "Size": convert_to_human_readable_size(11),
            "Type": "Dependency",
        }
    ]


def test_format_modules():
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

    assert format_modules(modules, platform, version) == expected_output


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
        result = get_files(repo_path, compressed=False, py_version="3.12")

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


def test_check_version():
    with (
        patch(
            "ddev.cli.size.utils.common_funcs.load_toml_file",
            return_value={"project": {"classifiers": ["Programming Language :: Python :: 3.12"]}},
        ),
        patch("ddev.cli.size.utils.common_funcs.os.path.exists", return_value=True),
    ):
        assert check_python_version("fake_repo", "integration1", "3")
        assert not check_python_version("fake_repo", "integration1", "2")


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


def test_save_csv():
    mock_file = mock_open()
    mock_app = MagicMock()

    modules = [
        {"Name": "module1", "Size_Bytes": 123, "Size": "2 B"},
        {"Name": "module,with,comma", "Size_Bytes": 456, "Size": "2 B"},
    ]

    with patch("ddev.cli.size.utils.common_funcs.open", mock_file):
        save_csv(mock_app, modules, "output.csv")

    mock_file.assert_called_once_with("output.csv", "w", encoding="utf-8")
    handle = mock_file()

    expected_writes = ["Name,Size_Bytes\n", "module1,123\n", '"module,with,comma",456\n']

    assert handle.write.call_args_list == [((line,),) for line in expected_writes]


def test_save_json():
    mock_app = MagicMock()
    mock_file = mock_open()

    modules = [
        {"name": "mod1", "size": "100"},
        {"name": "mod2", "size": "200"},
        {"name": "mod3", "size": "300"},
    ]

    with patch("ddev.cli.size.utils.common_funcs.open", mock_file):
        save_json(mock_app, "output.json", modules)

    mock_file.assert_called_once_with("output.json", "w", encoding="utf-8")
    handle = mock_file()

    expected_json = json.dumps(modules, indent=2)

    written_content = "".join(call.args[0] for call in handle.write.call_args_list)
    assert written_content == expected_json

    mock_app.display.assert_called_once_with("JSON file saved to output.json")


def test_save_markdown():
    mock_app = MagicMock()
    mock_file = mock_open()

    modules = [
        {"Name": "module1", "Size_Bytes": 123, "Size": "2 B", "Type": "Integration", "Platform": "linux-x86_64"},
        {"Name": "module2", "Size_Bytes": 456, "Size": "4 B", "Type": "Dependency", "Platform": "linux-x86_64"},
    ]

    with patch("ddev.cli.size.utils.common_funcs.open", mock_file):
        save_markdown(mock_app, "Status", modules, "output.md")

    mock_file.assert_called_once_with("output.md", "a", encoding="utf-8")
    handle = mock_file()

    expected_writes = (
        "# Status\n\n"
        "## Platform: linux-x86_64\n\n"
        "| Name | Size | Type | Platform |\n"
        "| --- | --- | --- | --- |\n"
        "| module1 | 2 B | Integration | linux-x86_64 |\n"
        "| module2 | 4 B | Dependency | linux-x86_64 |\n"
    )

    written_content = "".join(call.args[0] for call in handle.write.call_args_list)
    assert written_content == expected_writes


def test_extract_version_from_about_py_pathlib():
    fake_path = Path("some") / "module" / "__about__.py"
    fake_content = "__version__ = '1.2.3'\n"

    with patch("ddev.cli.size.utils.common_funcs.open", mock_open(read_data=fake_content)):
        version = extract_version_from_about_py(str(fake_path))

    assert version == "1.2.3"


def test_extract_version_from_about_py_no_version_pathlib():
    fake_path = Path("another") / "module" / "__about__.py"
    fake_content = "version = 'not_defined'\n"

    with patch("ddev.cli.size.utils.common_funcs.open", mock_open(read_data=fake_content)):
        version = extract_version_from_about_py(str(fake_path))

    assert version == ""


def test_get_org():
    mock_app = Mock()
    mock_path = Mock()

    toml_data = """
        [orgs.default]
        api_key = "test_api_key"
        app_key = "test_app_key"
        site = "datadoghq.com"
        """

    mock_app.config_file.path = mock_path

    with (
        patch("ddev.cli.size.utils.common_funcs.open", mock_open(read_data=toml_data)),
        patch.object(mock_path, "open", mock_open(read_data=toml_data)),
    ):
        result = get_org(mock_app, "default")

    expected = {
        "api_key": "test_api_key",
        "app_key": "test_app_key",
        "site": "datadoghq.com",
    }

    assert result == expected
