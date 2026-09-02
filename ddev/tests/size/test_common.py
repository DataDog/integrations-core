import io
import json
import os
import re
import zipfile
from unittest.mock import MagicMock, mock_open, patch

import pytest
import requests

from ddev.cli.size.utils.common_funcs import (
    _matches_gitignore,
    check_python_version,
    compress,
    convert_to_human_readable_size,
    export_format,
    extract_version_from_about_py,
    format_modules,
    get_dependencies_list,
    get_dependencies_sizes,
    get_files,
    get_gitignore_files,
    get_valid_platforms,
    get_valid_versions,
    is_correct_dependency,
    is_valid_integration_file,
    request_wheel,
    save_csv,
    save_json,
    save_markdown,
    send_diff_metrics_to_dd,
    wheel_url_candidates,
)
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
def test_is_correct_dependency(platform, version, dependency_file_name, expected):
    assert is_correct_dependency(platform, version, dependency_file_name) is expected


@pytest.mark.parametrize(
    "size_bytes, expected_string",
    [
        pytest.param(500, "500 B", id="Bytes"),
        pytest.param(1024, "1.0 KiB", id="KiB"),
        pytest.param(1048576, "1.0 MiB", id="MiB"),
        pytest.param(1073741824, "1.0 GiB", id="GiB"),
    ],
)
def test_convert_to_human_readable_size(size_bytes, expected_string):
    assert convert_to_human_readable_size(size_bytes) == expected_string


@pytest.mark.parametrize(
    "file_path, expected",
    [
        pytest.param("datadog_checks/example.py", True, id="valid"),
        pytest.param("__pycache__/file.py", False, id="pycache"),
        pytest.param("datadog_checks_dev/example.py", False, id="checks_dev"),
        pytest.param(".git/config", False, id="git"),
        pytest.param("datadog_checks/module/cache.pyc", False, id="gitignore_glob_ext"),
        pytest.param("datadog_checks/module/__pycache__/foo.py", False, id="gitignore_glob_dir"),
    ],
)
def test_is_valid_integration_file(file_path, expected):
    repo_path = "fake_repo"
    gitignore_patterns = ["*.pyc", "__pycache__"]
    with patch("ddev.cli.size.utils.common_funcs.get_gitignore_files", return_value=gitignore_patterns):
        assert is_valid_integration_file(to_native_path(file_path), repo_path) is expected


@pytest.mark.parametrize(
    "path, patterns, expected",
    [
        pytest.param("foo/bar/baz.pyc", ["*.pyc"], True, id="glob_extension_match"),
        pytest.param("foo/bar/baz.py", ["*.pyc"], False, id="glob_extension_no_match"),
        pytest.param("foo/__pycache__/module.py", ["__pycache__"], True, id="dir_segment_match"),
        pytest.param("foo/bar/module.py", ["__pycache__"], False, id="dir_segment_no_match"),
        pytest.param("foo/bar/notes.log", ["*.log"], True, id="glob_log_match"),
        pytest.param("foo/bar/notes.txt", ["*.log"], False, id="glob_log_no_match"),
        pytest.param("foo/bar/baz.py", ["*.pyc", "__pycache__", "*.log"], False, id="no_pattern_matches"),
        pytest.param("foo/__pycache__/baz.pyc", ["*.pyc", "__pycache__"], True, id="multiple_patterns_first_matches"),
    ],
)
def test_matches_gitignore(path, patterns, expected):
    assert _matches_gitignore(to_native_path(path), patterns) is expected


def test_get_dependencies_list():
    file_content = (
        "dependency1 @ https://example.com/${INTEGRATIONS_WHEELS_STORAGE}/dependency1/dependency1-1.1.1-.whl\n"
        "dependency2 @ https://example.com/${INTEGRATIONS_WHEELS_STORAGE}/dependency2/dependency2-1.1.1-.whl"
    )
    mock_open_obj = mock_open(read_data=file_content)
    with patch("builtins.open", mock_open_obj):
        deps, urls, versions = get_dependencies_list("fake_path")
    assert deps == ["dependency1", "dependency2"]
    # The storage tier placeholder is left unresolved here; it's resolved later when the wheel is requested.
    assert urls == [
        "https://example.com/${INTEGRATIONS_WHEELS_STORAGE}/dependency1/dependency1-1.1.1-.whl",
        "https://example.com/${INTEGRATIONS_WHEELS_STORAGE}/dependency2/dependency2-1.1.1-.whl",
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
    with patch("requests.get", return_value=mock_response) as mock_get:
        file_data = get_dependencies_sizes(
            MagicMock(),
            ["dependency1"],
            ["https://example.com/${INTEGRATIONS_WHEELS_STORAGE}/dependency1/dependency1-1.1.1-.whl"],
            ["1.1.1"],
            True,
            "dev",
        )

    # The storage tier placeholder must be resolved against the tier passed in, not left as-is.
    mock_get.assert_called_once_with("https://example.com/dev/dependency1/dependency1-1.1.1-.whl", stream=True)

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


def test_get_gitignore_files(tmp_path):
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(f"__pycache__{os.sep}\n*.log\n")
    assert get_gitignore_files(tmp_path) == ["__pycache__" + os.sep, "*.log"]


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
        save_markdown(mock_app, "Status", modules, "output.md", section_total="absolute")

    mock_file.assert_called_once_with("output.md", "a", encoding="utf-8")
    handle = mock_file()

    expected_writes = (
        "# Status\n\n"
        "<details>\n"
        "<summary>linux-x86_64 (579 B)</summary>\n\n"
        "| Name | Size | Type |\n"
        "| --- | --- | --- |\n"
        "| module1 | 2 B | Integration |\n"
        "| module2 | 4 B | Dependency |\n"
        "\n</details>\n"
    )

    written_content = "".join(call.args[0] for call in handle.write.call_args_list)
    assert written_content == expected_writes


@pytest.mark.parametrize(
    ("mode", "expected_title", "expected_total"),
    [
        pytest.param("status", "Status", "absolute", id="status"),
        pytest.param("diff", "Diff", "delta", id="diff"),
    ],
)
def test_export_format_titles_markdown_by_mode(mode, expected_title, expected_total):
    modules = [
        {"Name": "module1", "Size_Bytes": 123, "Size": "2 B", "Type": "Integration", "Platform": "linux-x86_64"},
    ]

    with patch("ddev.cli.size.utils.common_funcs.save_markdown") as mock_save:
        export_format(MagicMock(), ["markdown"], modules, mode, None, None, False)

    _, title, _, filename = mock_save.call_args.args
    assert title == expected_title
    assert filename == f"{mode}_uncompressed.md"
    assert mock_save.call_args.kwargs["section_total"] == expected_total


def test_save_markdown_signs_positive_totals_for_deltas():
    mock_app = MagicMock()
    mock_file = mock_open()

    modules = [
        {"Name": "module1", "Size_Bytes": 1000, "Size": "+1000 B", "Type": "Dependency", "Platform": "linux-x86_64"},
        {"Name": "module2", "Size_Bytes": -400, "Size": "-400 B", "Type": "Dependency", "Platform": "linux-x86_64"},
    ]

    with patch("ddev.cli.size.utils.common_funcs.open", mock_file):
        save_markdown(mock_app, "Diff", modules, "output.md", section_total="delta")

    written_content = "".join(call.args[0] for call in mock_file().write.call_args_list)
    assert "<summary>linux-x86_64 (+600 B)</summary>" in written_content


def test_save_markdown_leaves_negative_totals_unsigned():
    mock_app = MagicMock()
    mock_file = mock_open()

    modules = [
        {"Name": "module1", "Size_Bytes": -1000, "Size": "-1000 B", "Type": "Dependency", "Platform": "linux-x86_64"},
    ]

    with patch("ddev.cli.size.utils.common_funcs.open", mock_file):
        save_markdown(mock_app, "Diff", modules, "output.md", section_total="delta")

    written_content = "".join(call.args[0] for call in mock_file().write.call_args_list)
    assert "<summary>linux-x86_64 (-1000 B)</summary>" in written_content


def test_save_markdown_one_section_per_platform_and_version():
    mock_app = MagicMock()
    mock_file = mock_open()

    modules = [
        {
            "Name": "module1",
            "Size_Bytes": 100,
            "Size": "100 B",
            "Type": "Dependency",
            "Platform": "linux-x86_64",
            "Python_Version": "3.13",
        },
        {
            "Name": "module1",
            "Size_Bytes": 200,
            "Size": "200 B",
            "Type": "Dependency",
            "Platform": "macos-aarch64",
            "Python_Version": "3.13",
        },
    ]

    with patch("ddev.cli.size.utils.common_funcs.open", mock_file):
        save_markdown(mock_app, "Status", modules, "output.md", section_total="absolute")

    written_content = "".join(call.args[0] for call in mock_file().write.call_args_list)
    assert written_content.count("<details>") == 2
    assert "<summary>linux-x86_64, Python 3.13 (100 B)</summary>" in written_content
    assert "<summary>macos-aarch64, Python 3.13 (200 B)</summary>" in written_content
    assert "Python_Version" not in written_content


def test_save_markdown_orders_sections_deterministically():
    platforms = ["windows-x86_64", "linux-aarch64", "macos-x86_64", "linux-x86_64", "macos-aarch64"]
    modules = [
        {
            "Name": "module1",
            "Size_Bytes": 100,
            "Size": "100 B",
            "Type": "Integration",
            "Platform": platform,
            "Python_Version": "3.13",
        }
        for platform in platforms
    ]

    mock_file = mock_open()
    with patch("ddev.cli.size.utils.common_funcs.open", mock_file):
        save_markdown(MagicMock(), "Diff", modules, "output.md", section_total="delta")

    written_content = "".join(call.args[0] for call in mock_file().write.call_args_list)
    assert re.findall(r"<summary>(\S+), Python", written_content) == sorted(platforms)


def test_send_diff_metrics_to_dd_metric_shape():
    modules = [
        {
            "Name": "dep1",
            "Version": "1.0.0 -> 1.1.0",
            "Type": "Dependency",
            "Size_Bytes": 500,
            "Size": "+500 B",
            "Platform": "linux-aarch64",
            "Python_Version": "3.12",
        },
        {
            "Name": "path1.py (DELETED)",
            "Version": "1.0.0",
            "Type": "Integration",
            "Size_Bytes": -1000,
            "Size": "-1000 B",
            "Platform": "linux-aarch64",
            "Python_Version": "3.12",
        },
    ]

    with (
        patch("ddev.cli.size.utils.common_funcs.initialize"),
        patch(
            "ddev.cli.size.utils.common_funcs.get_commit_data",
            return_value=(1700000000, "Bump dep1 (#123)", ["AI-1"], ["123"]),
        ),
        patch("ddev.cli.size.utils.common_funcs.api.Metric.send", return_value={"status": "ok"}) as mock_metric_send,
    ):
        send_diff_metrics_to_dd(MagicMock(), "commit2", modules, None, "fake_key", False)

    metrics = mock_metric_send.call_args.kwargs["metrics"]
    assert len(metrics) == 2
    assert {m["metric"] for m in metrics} == {"datadog.agent_integrations.size_diff"}
    assert [m["points"] for m in metrics] == [[(1700000000, 500)], [(1700000000, -1000)]]
    assert "name:dep1" in metrics[0]["tags"]
    assert "compression:uncompressed" in metrics[0]["tags"]
    assert "pr_number:123" in metrics[0]["tags"]
    assert "name:path1.py" in metrics[1]["tags"]
    assert "name_type:Integration(path1.py)" in metrics[1]["tags"]


@pytest.mark.parametrize(
    "file_content, expected_version",
    [
        pytest.param("__version__ = '1.2.3'", "1.2.3", id="version_present"),
        pytest.param("not_version = 'not_defined'", "", id="version_not_present"),
    ],
)
def test_extract_version_from_about_py(file_content, expected_version):
    fake_path = Path("some") / "module" / "__about__.py"
    with patch("ddev.cli.size.utils.common_funcs.open", mock_open(read_data=file_content)):
        version = extract_version_from_about_py(str(fake_path))
    assert version == expected_version


PLACEHOLDER_URL = "https://example.com/${INTEGRATIONS_WHEELS_STORAGE}/built/dep1/dep1-1.1.1-.whl"


def make_wheel_response(status_code):
    response = MagicMock()
    response.status_code = status_code
    if status_code >= 400:
        error = requests.HTTPError(response=response)
        response.raise_for_status.side_effect = error
    else:
        response.raise_for_status.return_value = None
    return response


@pytest.mark.parametrize(
    "wheels_storage, expected",
    [
        pytest.param(
            "dev",
            [
                "https://example.com/dev/built/dep1/dep1-1.1.1-.whl",
                "https://example.com/stable/built/dep1/dep1-1.1.1-.whl",
            ],
            id="dev",
        ),
        pytest.param(
            "stable",
            [
                "https://example.com/stable/built/dep1/dep1-1.1.1-.whl",
                "https://example.com/dev/built/dep1/dep1-1.1.1-.whl",
            ],
            id="stable",
        ),
    ],
)
def test_wheel_url_candidates_prefers_configured_tier(wheels_storage, expected):
    assert wheel_url_candidates(PLACEHOLDER_URL, wheels_storage) == expected


def test_wheel_url_candidates_without_placeholder_is_not_duplicated():
    url = "https://example.com/built/dep1/dep1-1.1.1-.whl"
    assert wheel_url_candidates(url, "dev") == [url]


@pytest.mark.parametrize("missing_status_code", [404, 403], ids=["not_found", "forbidden"])
def test_request_wheel_falls_back_to_the_other_tier(missing_status_code):
    missing = make_wheel_response(missing_status_code)
    found = make_wheel_response(200)

    with patch("requests.get", side_effect=[missing, found]) as mock_get:
        assert request_wheel(MagicMock(), PLACEHOLDER_URL, "dev") is found

    assert [call.args[0] for call in mock_get.call_args_list] == [
        "https://example.com/dev/built/dep1/dep1-1.1.1-.whl",
        "https://example.com/stable/built/dep1/dep1-1.1.1-.whl",
    ]
    missing.close.assert_called_once()


def test_request_wheel_raises_when_no_tier_has_the_wheel():
    with patch("requests.get", side_effect=[make_wheel_response(404), make_wheel_response(404)]):
        with pytest.raises(
            requests.HTTPError,
            match=re.escape(
                "Tried: https://example.com/dev/built/dep1/dep1-1.1.1-.whl (404), "
                "https://example.com/stable/built/dep1/dep1-1.1.1-.whl (404)"
            ),
        ):
            request_wheel(MagicMock(), PLACEHOLDER_URL, "dev")


def test_request_wheel_does_not_retry_on_a_non_missing_error():
    with patch("requests.get", side_effect=[make_wheel_response(500), make_wheel_response(200)]) as mock_get:
        with pytest.raises(requests.HTTPError):
            request_wheel(MagicMock(), PLACEHOLDER_URL, "dev")

    assert mock_get.call_count == 1


def test_request_wheel_uses_head_when_requested():
    found = make_wheel_response(200)

    with patch("requests.head", return_value=found) as mock_head:
        assert request_wheel(MagicMock(), PLACEHOLDER_URL, "stable", head=True) is found

    mock_head.assert_called_once_with("https://example.com/stable/built/dep1/dep1-1.1.1-.whl")
