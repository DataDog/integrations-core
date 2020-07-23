# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.rethinkdb.version import parse_version

from ..common import MALFORMED_VERSION_STRING_PARAMS


@pytest.mark.unit
@pytest.mark.parametrize(
    'version_string, expected_version',
    [
        pytest.param('rethinkdb 2.4.0~0bionic (CLANG 6.0.0 (tags/RELEASE_600/final))', '2.4.0', id='2.4'),
        pytest.param('rethinkdb 2.4.0-beta~0bionic (debug)', '2.4.0', id='2.4-beta'),
        pytest.param('rethinkdb 2.4.0~0bionic (debug)', '2.4.0', id='2.4-debug'),
        pytest.param('rethinkdb 2.3.3~0jessie (GCC 4.9.2)', '2.3.3', id='2.3'),
        pytest.param('rethinkdb 2.3.6 (GCC 4.9.2)', '2.3.6', id='2.3-no-build'),
        pytest.param('rethinkdb 2.3.3', '2.3.3', id='no-compilation-string'),
    ],
)
def test_parse_version(version_string, expected_version):
    # type: (str, str) -> None
    assert parse_version(version_string) == expected_version


@pytest.mark.unit
@pytest.mark.parametrize('version_string', MALFORMED_VERSION_STRING_PARAMS)
def test_parse_malformed_version(version_string):
    # type: (str) -> None
    with pytest.raises(ValueError):
        parse_version(version_string)
