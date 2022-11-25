# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.tooling.license_headers import parse_license_header


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


@pytest.mark.parametrize("license_line", [
    "# Licensed under a 3-clause BSD style license (see LICENSE)",
    "# Licensed under Simplified BSD License (see LICENSE)"
])
def test_parse_license_header_different_licenses(license_line):
    expected_header = """# (C) Foo, Inc. 2000-present
# All rights reserved
# {license_line}"""

    file_contents = f"{expected_header}\n\nimport os"
    assert parse_license_header(file_contents) == expected_header
