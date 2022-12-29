# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from contextlib import contextmanager

import mock
import pytest

from datadog_checks.base.stubs import aggregator
from datadog_checks.base.utils.tracing import INTEGRATION_TRACING_SERVICE_NAME, traced_class


class MockAgentCheck(object):
    def __init__(self, *args, **kwargs):
        self.name = args[0]
        self.init_config = args[1]
        self.instances = args[2]
        self.check_id = ''

    def run(self):
        self.check(self.instances[0])

    def check(self, instance):
        raise NotImplementedError

    def gauge(self, name, value):
        aggregator.submit_metric(self, self.check_id, aggregator.GAUGE, name, value, [], 'hostname', False)


class DummyCheck(MockAgentCheck):
    def __init__(self, *args, **kwargs):
        super(DummyCheck, self).__init__(*args, **kwargs)

    def check(self, _):
        self.gauge('dummy.metric', 10)
        self.dummy_method()

    def dummy_method(self):
        self.gauge('foo', 10)


@contextmanager
def traced_mock_classes():
    # temporarily unset the DDEV_TRACE_ENABLED flag to enable testing
    # the exhaustive tracing option
    ddev_trace_enabled = os.environ.pop('DDEV_TRACE_ENABLED', None)
    # the mock classes must be traced within a single test execution in order for
    # us to be able to control the parameters used by the traced_class wrapper
    # The regular AgentCheck common base class applies traced_class but here
    # in the test to keep things simple we trace both base and child classes directly
    global MockAgentCheck, DummyCheck
    orig_mock_agent, orig_dummy = MockAgentCheck, DummyCheck
    MockAgentCheck, DummyCheck = traced_class(MockAgentCheck), traced_class(DummyCheck)
    yield
    MockAgentCheck, DummyCheck = orig_mock_agent, orig_dummy
    if ddev_tracce_enabled:
        os.environ['DDEV_TRACE_ENABLED'] = ddev_trace_enabled


@pytest.mark.parametrize(
    'integration_tracing', [pytest.param(False, id="tracing_false"), pytest.param(True, id="tracing_true")]
)
@pytest.mark.parametrize(
    'integration_tracing_exhaustive',
    [pytest.param(False, id="exhaustive_false"), pytest.param(True, id="exhaustive_true")],
)
def test_traced_class(integration_tracing, integration_tracing_exhaustive, datadog_agent):
    def _get_config(key):
        return {
            'integration_tracing': str(integration_tracing).lower(),
            'integration_tracing_exhaustive': str(integration_tracing_exhaustive).lower(),
        }.get(key, None)

    with mock.patch.object(datadog_agent, 'get_config', _get_config), mock.patch('ddtrace.tracer') as tracer:

        with traced_mock_classes():
            check = DummyCheck('dummy', {}, [{}])
            check.run()

        if integration_tracing:
            called_services = set([c.kwargs['service'] for c in tracer.trace.mock_calls if 'service' in c.kwargs])
            called_methods = set([c.args[0] for c in tracer.trace.mock_calls if c.args])

            assert called_services == {INTEGRATION_TRACING_SERVICE_NAME}
            assert 'run' in called_methods, "'run' must always be traced"

            exhaustive_only_methods = {'__init__', 'check', 'dummy_method'}
            if integration_tracing_exhaustive:
                for m in exhaustive_only_methods:
                    assert m in called_methods
            else:
                for m in exhaustive_only_methods:
                    assert m not in called_methods
        else:
            tracer.trace.assert_not_called()
