# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

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

    def gauge(self, name, value):
        aggregator.submit_metric(self, self.check_id, aggregator.GAUGE, name, value, [], 'hostname', False)


class DummyCheck(MockAgentCheck):
    def __init__(self, *args, **kwargs):
        super(DummyCheck, self).__init__(*args, **kwargs)
        self.checked = False

    def check(self, instance):
        self.gauge('dummy.metric', 10)


@pytest.mark.parametrize('traces_enabled', [pytest.param('false'), (pytest.param('true'))])
def test_traced_class(traces_enabled):
    with mock.patch.dict(os.environ, {'DDEV_TRACE_ENABLED': traces_enabled}, clear=True), mock.patch(
        'ddtrace.tracer'
    ) as tracer:
        TracedDummyClass = traced_class(DummyCheck)

        check = TracedDummyClass('dummy', {}, [{}])
        check.check({})

        if os.environ['DDEV_TRACE_ENABLED'] == 'true':
            tracer.trace.assert_has_calls(
                [
                    mock.call('__init__', resource='dummy', service=INTEGRATION_TRACING_SERVICE_NAME),
                    mock.call('check', resource='dummy', service=INTEGRATION_TRACING_SERVICE_NAME),
                ],
                any_order=True,
            )
        else:
            tracer.trace.assert_not_called()
