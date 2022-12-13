# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pathlib

import pytest

from datadog_checks.dev.tooling.license_headers import parse_license_header, validate_license_headers
from datadog_checks.dev.tooling.utils import get_license_header


@pytest.mark.parametrize("years", ["2000-present", "2001-2003", "2014"])
@pytest.mark.parametrize("holder", ["Datadog, Inc.", "Foo Bar", "Foo Bar <foo@bar.com>"])
def test_parse_license_header(years, holder):
    expected_header = f"""# (C) {holder} {years}
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)"""

    file_contents = f"{expected_header}\n\nimport os"
    assert parse_license_header(file_contents) == expected_header


def test_parse_license_header_empty_input():
    assert parse_license_header("") == ""


def test_parse_license_header_no_license():
    file_contents = "import os\n"

    assert parse_license_header(file_contents) == ""


def test_parse_license_header_multiple_holders():
    expected_header = """# (C) Foo, Inc. 2000-present
# (C) Mr. Bar <bar@bar.com> 2013
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)"""

    file_contents = f"{expected_header}\n\nimport os"
    assert parse_license_header(file_contents) == expected_header


@pytest.mark.parametrize(
    "license_line",
    [
        "# Licensed under a 3-clause BSD style license (see LICENSE)",
        "# Licensed under Simplified BSD License (see LICENSE)",
    ],
)
def test_parse_license_header_different_licenses(license_line):
    expected_header = """# (C) Foo, Inc. 2000-present
# All rights reserved
# {license_line}"""

    file_contents = f"{expected_header}\n\nimport os"
    assert parse_license_header(file_contents) == expected_header


def test_validate_license_headers_returns_no_errors_when_directory_is_empty(tmp_path):
    assert validate_license_headers(tmp_path) == []


def test_validate_license_headers_returns_error_for_a_file_without_license(tmp_path):
    check_path = tmp_path / "check"
    check_path.mkdir()

    with open(check_path / "setup.py", "w") as f:
        f.write(
            """
import os
"""
        )

    errors = validate_license_headers(check_path)
    assert len(errors) == 1
    assert errors[0].message == "missing license header"
    assert errors[0].path == "setup.py"


def test_validate_license_headers_when_all_files_have_valid_headers_returns_empty_list(tmp_path):
    check_path = tmp_path / "check"
    check_path.mkdir()

    with open(check_path / "setup.py", "w") as f:
        f.write(
            f"""{get_license_header()}

import os
"""
        )

    assert validate_license_headers(check_path, get_previous=_make_get_previous()) == []


def test_validate_license_headers_works_with_arbitrary_nesting(tmp_path):
    check_path = tmp_path / "check"
    check_path.mkdir()

    nested_path = check_path / "datadog_checks/check"
    nested_path.mkdir(parents=True)
    with open(nested_path / "check.py", "w") as f:
        f.write(
            """
import os
"""
        )

    errors = validate_license_headers(check_path)
    assert len(errors) == 1
    assert errors[0].message == "missing license header"
    assert errors[0].path == "datadog_checks/check/check.py"


def test_validate_license_headers_skips_non_python_files(tmp_path):
    check_path = tmp_path / "check"
    check_path.mkdir()

    with open(check_path / "pyproject.toml", "w") as f:
        f.write("[something]\n")

    assert validate_license_headers(check_path) == []


@pytest.mark.parametrize(
    "relpath",
    [
        ".hidden",
        ".hidden/subfolder",
        "tests/docker",
        "tests/docker/subfolder",
    ],
)
def test_validate_license_headers_skips_blacklisted_folders(tmp_path, relpath):
    check_path = tmp_path / "check"
    target_path = check_path / relpath
    target_path.mkdir(parents=True)

    with open(target_path / "some.py", "w") as f:
        f.write("import os\n")

    assert validate_license_headers(check_path, ignore=[pathlib.Path("tests/docker")]) == []


def test_validate_license_headers_returns_error_on_new_file_with_header_not_matching_template(tmp_path):
    check_path = tmp_path / "check"
    check_path.mkdir()

    with open(check_path / "setup.py", "w") as f:
        f.write(
            """# (C) Foo, Inc. 1999-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
"""
        )

    errors = validate_license_headers(check_path, get_previous=_make_get_previous())
    assert len(errors) == 1
    assert errors[0].message == "file does not match expected license format"
    assert errors[0].path == "setup.py"


def test_validate_license_headers_returns_error_on_existing_file_with_changed_header(tmp_path):
    check_path = tmp_path / "check"
    check_path.mkdir()

    original_license = """# (C) Foo, Inc. 1999-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""

    prev_contents = f"{original_license}\n\nimport os\n"

    with open(check_path / "setup.py", "w") as f:
        f.write(
            """# (C) Foo, Inc. 2000-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
"""
        )

    with open(check_path / "unchanged_file.py", "w") as f:
        f.write(prev_contents)

    fake_get_previous = _make_get_previous(
        {
            pathlib.Path(check_path / "setup.py"): prev_contents,
            pathlib.Path(check_path / "unchanged_file.py"): prev_contents,
        }
    )

    errors = validate_license_headers(check_path, get_previous=fake_get_previous)
    assert len(errors) == 1
    assert errors[0].message == "existing file has changed license"
    assert errors[0].path == "setup.py"


def _make_get_previous(d: dict = None):
    if d is None:
        d = {}

    def _fake_get_previous(path):
        return d.get(path)

    return _fake_get_previous
