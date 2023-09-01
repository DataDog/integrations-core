# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import sys

import pytest

from datadog_checks.dev import run_command
from datadog_checks.dev.tooling.commands.release.make import validate_version


@pytest.mark.parametrize(
    'version',
    [
        pytest.param("", id='empty'),
        pytest.param("1", id='only major'),
        pytest.param("1.2", id='no patch'),
        pytest.param("1.2.3-alpha", id='alpha with no number'),
        pytest.param("1.2-alpha.1", id='alpha with no patch'),
        pytest.param("1-alpha.1", id='alpha with no minor'),
        pytest.param("1.2.3-alpha.1a", id='alpha with extra chars'),
    ],
)
def test_release_make_with_invalid_input_version(version):
    result = run_command(
        [sys.executable, '-m', 'datadog_checks.dev', '-x', 'release', 'make', 'my_check', '--version', version],
        capture=True,
    )

    assert result.code == 2
    assert result.stdout == ""
    assert (
        "Invalid value for '--version': must match `^\\d+\\.\\d+\\.\\d+(-(rc|pre|alpha|beta)\\.\\d+)?$" in result.stderr
    )


@pytest.mark.parametrize(
    'version',
    [
        "1.2.3",
        "1.2.3-alpha.1",
        "1.2.3-alpha.12",
        "1.2.3-beta.1",
        "1.2.3-rc.1",
        "1.2.3-pre.1",
        None,
    ],
)
# TODO: replace this test with a one that calls `ddev release make` directly
#  once we move the command to the new ddev cli
def test_validate_version(version):
    assert version == validate_version(None, None, version)
