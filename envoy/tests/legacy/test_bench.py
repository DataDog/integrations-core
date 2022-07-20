import pytest

from datadog_checks.envoy import Envoy

from .common import INSTANCES


@pytest.mark.usefixtures('dd_environment')
def test_run(benchmark):
    instance = INSTANCES['main']
    c = Envoy('envoy', {}, [instance])

    # Run once to get logging of unknown metrics out of the way.
    c.check(instance)

    benchmark(c.check, instance)


def test_fixture(benchmark, fixture_path, mock_http_response):
    instance = INSTANCES['main']
    c = Envoy('envoy', {}, [instance])

    mock_http_response(file_path=fixture_path('multiple_services'))

    # Run once to get logging of unknown metrics out of the way.
    c.check(instance)

    benchmark(c.check, instance)
