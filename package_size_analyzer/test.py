
import pytest
import requests
from unittest.mock import patch, mock_open, MagicMock
from modes import (
    get_compressed_dependencies,
    get_gitignore_files,
    convert_size,
    is_valid_integration,
    is_correct_dependency,
    get_dependencies,
    get_dependencies_sizes
)

def test_is_correct_dependency():
    assert is_correct_dependency("windows-x86_64", "3.12", "windows-x86_64-3.12") == True
    assert is_correct_dependency("windows-x86_64", "3.12", "linux-x86_64-3.12") == False
    assert is_correct_dependency("windows-x86_64", "3.13", "windows-x86_64-3.12") == False

   
def test_convert_size():
    assert convert_size(500) == "500B"
    assert convert_size(1024) == "1.0KB"
    assert convert_size(1048576) == "1.0MB"
    assert convert_size(1073741824) == "1.0GB"

def test_is_valid_integration():
    included_folder = "datadog_checks/"
    ignored_files = {"datadog_checks_dev", "datadog_checks_tests_helper"}
    git_ignore = [".git", "__pycache__"]
    
    assert is_valid_integration("datadog_checks/example.py", included_folder, ignored_files, git_ignore) == True
    assert is_valid_integration("__pycache__/file.py", included_folder, ignored_files, git_ignore) == False
    assert is_valid_integration("datadog_checks_dev/example.py", included_folder, ignored_files, git_ignore) == False
    assert is_valid_integration(".git/config", included_folder, ignored_files, git_ignore) == False

def test_get_dependencies():
    file_content = "dependency1 @ https://example.com/dependency1.whl\ndependency2 @ https://example.com/dependency2.whl"
    mock_open_obj = mock_open(read_data=file_content)
    with patch("builtins.open", mock_open_obj):
        deps, urls = get_dependencies("fake_path")
    assert deps == ["dependency1", "dependency2"]
    assert urls == ["https://example.com/dependency1.whl", "https://example.com/dependency2.whl"]

def test_get_gitignore_files():
    mock_gitignore = "__pycache__/\n*.log\n"  # Sample .gitignore file
    with patch("builtins.open", mock_open(read_data=mock_gitignore)):
        with patch("os.path.exists", return_value=True):
            ignored_patterns = get_gitignore_files()
    assert ignored_patterns == ["__pycache__/", "*.log"]

def test_get_dependencies_sizes():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Length": "12345"}
    with patch("requests.head", return_value=mock_response):
        file_data = get_dependencies_sizes(["dependency1"], ["https://example.com/dependency1.whl"])
    assert file_data == [{"File Path": "dependency1", "Type": "Dependency", "Name": "dependency1", "Size (Bytes)": 12345}]
