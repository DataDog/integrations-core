import pytest

from ddev.utils.integration_naming import integration_dir_name


@pytest.mark.parametrize(
    'name, expected',
    [
        pytest.param('simple', 'simple', id='already-normalized'),
        pytest.param('HPE Aruba Edge', 'hpe_aruba_edge', id='spaces-and-case'),
        pytest.param('my-cool.Check', 'my_cool_check', id='mixed-separators'),
        pytest.param('a--b..c  d', 'a_b_c_d', id='separator-runs-collapse'),
    ],
)
def test_integration_dir_name_normalizes(name, expected):
    assert integration_dir_name(name) == expected


@pytest.mark.parametrize(
    'name',
    [
        pytest.param('', id='empty'),
        pytest.param('   ', id='whitespace-only'),
        pytest.param('---', id='separators-only'),
        pytest.param('-leading', id='leading-separator'),
        pytest.param('trailing-', id='trailing-separator'),
        pytest.param('café', id='non-ascii'),
        pytest.param('datadog_operator', id='reserved-prefix'),
        pytest.param('DATADOG-anything', id='reserved-prefix-case-insensitive'),
        pytest.param('ddev/src', id='separator'),
        pytest.param('../escape', id='parent-traversal'),
        pytest.param('/etc', id='absolute'),
        pytest.param(None, id='none'),
        pytest.param(123, id='non-string'),
    ],
)
def test_integration_dir_name_rejects(name):
    with pytest.raises(ValueError, match='Invalid integration name'):
        integration_dir_name(name)
