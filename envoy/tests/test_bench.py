import mock
import pytest

from datadog_checks.envoy import Envoy

from .common import INSTANCES, response

MOCK_HTTP_GET = 'datadog_checks.base.utils.http.requests.get'


@pytest.mark.usefixtures('dd_environment')
def test_run(benchmark):
    instance = INSTANCES['main']
    c = Envoy('envoy', {}, [instance])

    # Run once to get logging of unknown metrics out of the way.
    c.check(instance)

    benchmark(c.check, instance)


def test_fixture(benchmark):
    instance = INSTANCES['main']
    c = Envoy('envoy', {}, [instance])

    with mock.patch(MOCK_HTTP_GET, return_value=response('multiple_services')):
        # Run once to get logging of unknown metrics out of the way.
        c.check(instance)

        benchmark(c.check, instance)
