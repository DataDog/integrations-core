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


def _write_string_to_file(path, contents):
    with open(path, "w") as f:
        f.write(contents)


def _write_file_without_license(path):
    _write_string_to_file(
        path,
        """
import os
""",
    )


def test_validate_license_headers_returns_no_errors_when_directory_is_empty(tmp_path):
    assert validate_license_headers(tmp_path) == []


def test_validate_license_headers_returns_error_for_a_file_without_license(tmp_path):
    check_path = tmp_path / "check"
    check_path.mkdir()

    _write_file_without_license(check_path / "setup.py")

    errors = validate_license_headers(check_path, get_previous=_make_get_previous())
    assert len(errors) == 1
    assert errors[0].message == "missing license header"
    assert errors[0].path == "setup.py"
    assert errors[0].fixed == f"{get_license_header()}\n\nimport os\n"


def test_validate_license_headers_when_all_files_have_valid_headers_returns_empty_list(tmp_path):
    check_path = tmp_path / "check"
    check_path.mkdir()

    _write_string_to_file(
        check_path / "setup.py",
        f"""{get_license_header()}

import os
""",
    )

    assert validate_license_headers(check_path, get_previous=_make_get_previous()) == []


def test_validate_license_headers_handles_files_encoded_in_utf8_with_bom(tmp_path):
    """This tests that a utf8 bom at the beginning of the file doesn't prevent the
    validator from finding the header. We need that encoding in some files that contain
    non-ascii characters to make py2 use the right encoding.
    """
    check_path = tmp_path / "check"
    check_path.mkdir()

    with open(check_path / "setup.py", "w", encoding="utf-8-sig") as f:
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
    _write_file_without_license(nested_path / "check.py")

    errors = validate_license_headers(check_path, get_previous=_make_get_previous())
    assert len(errors) == 1
    assert errors[0].message == "missing license header"
    assert errors[0].path == "datadog_checks/check/check.py"


def test_validate_license_headers_skips_non_python_files(tmp_path):
    check_path = tmp_path / "check"
    check_path.mkdir()

    _write_string_to_file(check_path / "pyproject.toml", "[something]\n")

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

    _write_file_without_license(target_path / "some.py")

    assert validate_license_headers(check_path, ignore=[pathlib.Path("tests/docker")]) == []


def test_validate_license_headers_returns_error_on_new_file_with_header_not_matching_template(tmp_path):
    check_path = tmp_path / "check"
    check_path.mkdir()

    _write_string_to_file(
        check_path / "setup.py",
        """# (C) Foo, Inc. 1999-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
""",
    )

    errors = validate_license_headers(check_path, get_previous=_make_get_previous())
    assert len(errors) == 1
    assert errors[0].message == "file does not match expected license format"
    assert errors[0].path == "setup.py"
    assert errors[0].fixed == f"{get_license_header()}\n\nimport os\n"


def test_validate_license_headers_returns_error_on_existing_file_with_changed_header(tmp_path):
    check_path = tmp_path / "check"
    check_path.mkdir()

    original_license = """# (C) Foo, Inc. 1999-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)"""

    prev_contents = f"{original_license}\n\nimport os\n"

    _write_string_to_file(
        check_path / "setup.py",
        """# (C) Foo, Inc. 2000-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import sys
""",
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
    assert errors[0].fixed == f"{original_license}\n\nimport sys\n"


def test_validate_license_headers_accepts_any_header_when_previous_version_with_no_license_exists(tmp_path):
    check_path = tmp_path / "check"
    check_path.mkdir()

    prev_contents = "\n\nimport os\n"

    _write_string_to_file(
        check_path / "setup.py",
        """# (C) Foo, Inc. 2000-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
""",
    )

    fake_get_previous = _make_get_previous(
        {
            pathlib.Path(check_path / "setup.py"): prev_contents,
        }
    )

    assert validate_license_headers(check_path, get_previous=fake_get_previous) == []


def test_validate_license_headers_does_not_suggest_fix_for_missing_header_when_file_is_not_new(tmp_path):
    check_path = tmp_path / "check"
    check_path.mkdir()

    _write_file_without_license(check_path / "setup.py")
    fake_get_previous = _make_get_previous(
        {
            pathlib.Path(check_path / "setup.py"): "",
        }
    )

    errors = validate_license_headers(check_path, get_previous=fake_get_previous)
    assert len(errors) == 1
    assert errors[0].fixed is None


def _make_get_previous(d: dict = None):
    if d is None:
        d = {}

    def _fake_get_previous(path):
        return d.get(path)

    return _fake_get_previous


def test_validate_license_headers_honors_gitignore_file_on_check_path(tmp_path):
    check_path = tmp_path / "check"
    check_path.mkdir()

    # .gitignore at check_path
    _write_string_to_file(check_path / ".gitignore", "build/\n")

    target_path = check_path / "foo" / "build"
    target_path.mkdir(parents=True)

    _write_file_without_license(target_path / "some.py")

    assert validate_license_headers(check_path, get_previous=_make_get_previous()) == []


def test_validate_license_headers_honors_nested_gitignore_files_reincluding_file(tmp_path):
    check_path = tmp_path / "check"
    check_path.mkdir()

    # .gitignore at check_path allows `build/`
    _write_string_to_file(check_path / ".gitignore", "!build/\n")

    target_path = check_path / "foo" / "build"
    target_path.mkdir(parents=True)

    # .gitignore at subfolder matches `build/`, overriding the parent's gitignore
    _write_string_to_file(check_path / "foo" / ".gitignore", "build/\n")

    _write_file_without_license(target_path / "some.py")

    assert validate_license_headers(check_path, get_previous=_make_get_previous()) == []


def test_validate_license_headers_honors_gitignore_relative_patterns(tmp_path):
    # This refers to gitignore patterns that contain separators at the beginning
    # or middle of the pattern, as those patterns are relative to the folder
    # where the .gitignore file that defines them is.
    check_path = tmp_path / "check"

    target_path = check_path / "foo" / "build"
    target_path.mkdir(parents=True)

    # .gitignore defines '/build', which must be assumed to be relative to its folder
    _write_string_to_file(check_path / "foo" / ".gitignore", "/build/\n")

    _write_file_without_license(target_path / "some.py")

    assert validate_license_headers(check_path, get_previous=_make_get_previous()) == []

    # And the pattern lets a more nested build folder through
    target_path = check_path / "foo" / "deeper" / "build"
    target_path.mkdir(parents=True)
    _write_file_without_license(target_path / "some.py")

    errors = validate_license_headers(check_path, get_previous=_make_get_previous())
    assert len(errors) > 0
    assert errors[0].path == (target_path / "some.py").relative_to(check_path).as_posix()


def test_validate_license_headers_honors_gitignore_from_parents(tmp_path):
    # tmp_path is going to be our repo root.
    # In all of our integration repos the check is always directly under the root,
    # but we're assuming that the function we're testing doesn't know this, hence
    # the extra level here for this test.
    check_path = tmp_path / "some_folder" / "check"

    target_path = check_path / "foo"
    target_path.mkdir(parents=True)

    _write_string_to_file(tmp_path / ".gitignore", "!foo\n")

    _write_file_without_license(target_path / "some.py")

    errors = validate_license_headers(check_path, repo_root=tmp_path, get_previous=_make_get_previous())
    assert len(errors) > 0
    assert errors[0].path == (target_path / "some.py").relative_to(check_path).as_posix()

    # If we override this in a subdir, we shouldn't get an error
    _write_string_to_file(check_path / ".gitignore", "foo/\n")
    assert validate_license_headers(check_path, repo_root=tmp_path, get_previous=_make_get_previous()) == []
