import mock

from datadog_checks.envoy import Envoy
from .common import INSTANCES, response


def test_run(benchmark):
    instance = INSTANCES['main']
    c = Envoy('envoy', None, {}, [instance])

    # Run once to get logging of unknown metrics out of the way.
    c.check(instance)

    benchmark(c.check, instance)


def test_fixture(benchmark):
    instance = INSTANCES['main']
    c = Envoy('envoy', None, {}, [instance])

    with mock.patch('requests.get', return_value=response('multiple_services')):
        # Run once to get logging of unknown metrics out of the way.
        c.check(instance)

        benchmark(c.check, instance)
