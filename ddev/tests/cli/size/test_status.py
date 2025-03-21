# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest.mock import patch, mock_open, MagicMock
import os
from ddev.cli.size.status import (
    get_compressed_dependencies,
    get_gitignore_files,
    convert_size,
    is_valid_integration,
    is_correct_dependency,
    get_dependencies,
    get_dependencies_sizes,
    group_modules
)
from ddev.cli.application import Application


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

def test_get_dependencies(terminal):
    file_content = "dependency1 @ https://example.com/dependency1.whl\ndependency2 @ https://example.com/dependency2.whl"
    mock_open_obj = mock_open(read_data=file_content)
    with patch("builtins.open", mock_open_obj):
        deps, urls = get_dependencies(terminal, "fake_path")
    assert deps == ["dependency1", "dependency2"]
    assert urls == ["https://example.com/dependency1.whl", "https://example.com/dependency2.whl"]

def test_get_gitignore_files(terminal):
    mock_gitignore = "__pycache__/\n*.log\n"  # Sample .gitignore file
    with patch("builtins.open", mock_open(read_data=mock_gitignore)):
        with patch("os.path.exists", return_value=True):
            ignored_patterns = get_gitignore_files(terminal)
    assert ignored_patterns == ["__pycache__/", "*.log"]

def test_get_dependencies_sizes(terminal):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Length": "12345"}
    with patch("requests.head", return_value=mock_response):
        file_data = get_dependencies_sizes(terminal, ["dependency1"], ["https://example.com/dependency1.whl"])
    assert file_data == [{"File Path": "dependency1", "Type": "Dependency", "Name": "dependency1", "Size (Bytes)": 12345}]

def test_get_compressed_dependencies(terminal):
    platform = "windows-x86_64"
    version = "3.12"
    
    fake_file_content = "dependency1 @ https://example.com/dependency1.whl\ndependency2 @ https://example.com/dependency2.whl"
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Length": "12345"}
    
    with patch("os.path.exists", return_value=True), \
         patch("os.path.isdir", return_value=True), \
         patch("os.listdir", return_value=[f"{platform}-{version}"]), \
         patch("os.path.isfile", return_value=True), \
         patch("builtins.open", mock_open(read_data=fake_file_content)), \
         patch("requests.head", return_value=mock_response):
        
        file_data = get_compressed_dependencies(terminal, platform, version)
    
    assert file_data == [
        {"File Path": "dependency1", "Type": "Dependency", "Name": "dependency1", "Size (Bytes)": 12345},
        {"File Path": "dependency2", "Type": "Dependency", "Name": "dependency2", "Size (Bytes)": 12345},
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
        {"Name": "module1", "Type": "A", "Size (Bytes)": 4000, "Size": "3.91 KB", "Platform": "linux-aarch64", "Version": "3.12"},
        {"Name": "module2", "Type": "B", "Size (Bytes)": 3000, "Size": "2.93 KB", "Platform": "linux-aarch64", "Version": "3.12"},
        {"Name": "module3", "Type": "A", "Size (Bytes)": 4000, "Size": "3.91 KB", "Platform": "linux-aarch64", "Version": "3.12"},
    ]

    assert group_modules(modules, platform, version) == expected_output

def test_statu_no_args(ddev):
    result = ddev('size', 'status', '--compressed')
    assert result.exit_code == 0

def test_status(ddev):
    result = ddev('size', 'status', '--platform', 'linux-aarch64', '--python', '3.12', '--compressed')
    assert result.exit_code == 0

def test_status_csv(ddev):
    result = ddev('size', 'status', '--platform', 'linux-aarch64', '--python', '3.12', '--compressed', '--csv')
    assert result.exit_code == 0

def test_status_fail(ddev):
    result = ddev('size', 'status', '--platform', 'linux', '--python', '3.12', '--compressed')
    assert result.exit_code != 0

def test_status_fail2(ddev):
    result = ddev('size', 'status', '--platform', 'linux-aarch64', '--python', '2.10', '--compressed')
    assert result.exit_code != 0

def test_status_fail2(ddev):
    result = ddev('size', 'status', '--platform', 'linux', '--python' ,'2.10', '--compressed')
    assert result.exit_code != 0

