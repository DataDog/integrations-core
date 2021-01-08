{license_header}
import pytest


@pytest.fixture(scope='session')
def dd_environment():
    yield {{}}, {{'use_jmx': True}}
