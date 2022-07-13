import pytest

from ddev.utils.ci import running_in_ci
from ddev.utils.platform import Platform

PLATFORM = Platform()


@pytest.fixture(scope='session')
def helpers():
    # https://docs.pytest.org/en/latest/writing_plugins.html#assertion-rewriting
    pytest.register_assert_rewrite('tests.helpers.api')

    from .helpers import api

    return api


def pytest_runtest_setup(item):
    for marker in item.iter_markers():
        if marker.name == 'requires_ci' and not running_in_ci():  # no cov
            pytest.skip('Not running in CI')

        if marker.name == 'requires_windows' and not PLATFORM.windows:
            pytest.skip('Not running on Windows')

        if marker.name == 'requires_macos' and not PLATFORM.macos:
            pytest.skip('Not running on macOS')

        if marker.name == 'requires_linux' and not PLATFORM.linux:
            pytest.skip('Not running on Linux')

        if marker.name == 'requires_unix' and PLATFORM.windows:
            pytest.skip('Not running on a Linux-based platform')


def pytest_configure(config):
    config.addinivalue_line('markers', 'requires_windows: Tests intended for Windows operating systems')
    config.addinivalue_line('markers', 'requires_macos: Tests intended for macOS operating systems')
    config.addinivalue_line('markers', 'requires_linux: Tests intended for Linux operating systems')
    config.addinivalue_line('markers', 'requires_unix: Tests intended for Linux-based operating systems')
