import pytest

from datadog_checks.rethinkdb._version import parse_version


@pytest.mark.unit
@pytest.mark.parametrize(
    'version_string, expected_version',
    [
        pytest.param('rethinkdb 2.4.0~0bionic (CLANG 6.0.0 (tags/RELEASE_600/final))', '2.4.0~0bionic', id='2.4'),
        pytest.param('rethinkdb 2.4.0-beta~0bionic (debug)', '2.4.0-beta~0bionic', id='2.4-beta'),
        pytest.param('rethinkdb 2.4.0~0bionic (debug)', '2.4.0~0bionic', id='2.4-debug'),
        pytest.param('rethinkdb 2.3.3~0jessie (GCC 4.9.2)', '2.3.3~0jessie', id='2.3'),
        pytest.param('rethinkdb 2.3.3 (GCC 4.9.2)', '2.3.3', id='2.3-no-build'),
    ],
)
def test_parse_version(version_string, expected_version):
    # type: (str, str) -> None
    assert parse_version(version_string) == expected_version
