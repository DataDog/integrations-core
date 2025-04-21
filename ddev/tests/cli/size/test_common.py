from unittest.mock import MagicMock, mock_open, patch

from ddev.cli.size.common import (
    compress,
    convert_size,
    get_dependencies_list,
    get_dependencies_sizes,
    get_gitignore_files,
    group_modules,
    is_correct_dependency,
    is_valid_integration,
    print_csv,
    valid_platforms_versions,
)


def test_valid_platforms_versions():
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
    expected_versions = {"3.12"}
    with patch("os.listdir", return_value=filenames):
        platforms, versions = valid_platforms_versions("/tmp/fake_repo")
        assert platforms == expected_platforms
        assert versions == expected_versions


def test_is_correct_dependency():
    assert is_correct_dependency("windows-x86_64", "3.12", "windows-x86_64-3.12")
    assert not is_correct_dependency("windows-x86_64", "3.12", "linux-x86_64-3.12")
    assert not is_correct_dependency("windows-x86_64", "3.13", "windows-x86_64-3.12")


def test_convert_size():
    assert convert_size(500) == "500 B"
    assert convert_size(1024) == "1.0 KB"
    assert convert_size(1048576) == "1.0 MB"
    assert convert_size(1073741824) == "1.0 GB"


def test_is_valid_integration():
    included_folder = "datadog_checks/"
    ignored_files = {"datadog_checks_dev", "datadog_checks_tests_helper"}
    git_ignore = [".git", "__pycache__"]

    assert is_valid_integration("datadog_checks/example.py", included_folder, ignored_files, git_ignore)
    assert not is_valid_integration("__pycache__/file.py", included_folder, ignored_files, git_ignore)
    assert not is_valid_integration("datadog_checks_dev/example.py", included_folder, ignored_files, git_ignore)
    assert not is_valid_integration(".git/config", included_folder, ignored_files, git_ignore)


def test_get_dependencies_list():
    file_content = (
        "dependency1 @ https://example.com/dependency1.whl\ndependency2 @ https://example.com/dependency2.whl"
    )
    mock_open_obj = mock_open(read_data=file_content)
    with patch("builtins.open", mock_open_obj):
        deps, urls = get_dependencies_list("fake_path")
    assert deps == ["dependency1", "dependency2"]
    assert urls == ["https://example.com/dependency1.whl", "https://example.com/dependency2.whl"]


def test_get_dependencies_sizes():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Length": "12345"}
    with patch("requests.head", return_value=mock_response):
        file_data = get_dependencies_sizes(["dependency1"], ["https://example.com/dependency1.whl"], True)
    assert file_data == [
        {"File Path": "dependency1", "Type": "Dependency", "Name": "dependency1", "Size (Bytes)": 12345}
    ]


def test_group_modules():
    modules = [
        {"Name": "module1", "Type": "A", "Size (Bytes)": 1500},
        {"Name": "module2", "Type": "B", "Size (Bytes)": 3000},
        {"Name": "module1", "Type": "A", "Size (Bytes)": 2500},
        {"Name": "module3", "Type": "A", "Size (Bytes)": 4000},
    ]

    platform = "linux-aarch64"
    version = "3.12"

    expected_output = [
        {
            "Name": "module1",
            "Type": "A",
            "Size (Bytes)": 4000,
            "Size": "3.91 KB",
            "Platform": "linux-aarch64",
            "Version": "3.12",
        },
        {
            "Name": "module2",
            "Type": "B",
            "Size (Bytes)": 3000,
            "Size": "2.93 KB",
            "Platform": "linux-aarch64",
            "Version": "3.12",
        },
        {
            "Name": "module3",
            "Type": "A",
            "Size (Bytes)": 4000,
            "Size": "3.91 KB",
            "Platform": "linux-aarch64",
            "Version": "3.12",
        },
    ]

    assert group_modules(modules, platform, version, 0) == expected_output


def test_get_gitignore_files():
    mock_gitignore = "__pycache__/\n*.log\n"  # Sample .gitignore file
    repo_path = "/fake/repo"
    with patch("builtins.open", mock_open(read_data=mock_gitignore)):
        with patch("os.path.exists", return_value=True):
            ignored_patterns = get_gitignore_files(repo_path)
    assert ignored_patterns == ["__pycache__/", "*.log"]


def test_compress():
    fake_content = b'a' * 16384
    original_size = len(fake_content)

    m = mock_open(read_data=fake_content)
    with patch("builtins.open", m):
        compressed_size = compress("fake/path/file.py")

    assert isinstance(compressed_size, int)
    assert compressed_size > 0
    assert compressed_size < original_size


def test_print_csv():
    mock_app = MagicMock()
    modules = [
        {"Name": "module1", "Size B": 123, "Size": "2 B"},
        {"Name": "module,with,comma", "Size B": 456, "Size": "2 B"},
    ]

    print_csv(mock_app, i=0, modules=modules)

    expected_calls = [
        (("Name,Size B",),),
        (('module1,123',),),
        (('"module,with,comma",456',),),
    ]

    actual_calls = mock_app.display.call_args_list
    assert actual_calls == expected_calls
