# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import mock
import pytest

from datadog_checks.base.stubs import aggregator
from datadog_checks.base.utils.tracing import traced, traced_class


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

    @traced
    def check(self, instance):
        self.gauge('dummy.metric', 10)


@pytest.mark.parametrize(
    'agent_config, init_config, called',
    [
        pytest.param({}, {}, False, id='agent_notset_init_notset_notcalled'),
        pytest.param({'integration_tracing': True}, {}, False, id='agent_true_init_notset_notcalled'),
        pytest.param(
            {'integration_tracing': True}, {'trace_check': False}, False, id='agent_true_init_false_notcalled'
        ),
        pytest.param(
            {'integration_tracing': False}, {'trace_check': False}, False, id='agent_false_init_false_notcalled'
        ),
        pytest.param({}, {'trace_check': True}, False, id='agent_notset_init_true_notcalled'),
        pytest.param(
            {'integration_tracing': False}, {'trace_check': True}, False, id='agent_false_init_true_notcalled'
        ),
        pytest.param(
            {'integration_tracing': True, 'integration_tracing_futures': False},
            {'trace_check': True},
            True,
            id='agent_true_init_true_called',
        ),
        pytest.param(
            {'integration_tracing': True, 'integration_tracing_futures': True},
            {'trace_check': True},
            True,
            id='agent_true_futures_true_init_true_called',
        ),
    ],
)
def test_traced(aggregator, agent_config, init_config, called):
    check = DummyCheck('dummy', init_config, [{}])

    with mock.patch('datadog_checks.base.utils.tracing.datadog_agent') as datadog_agent, mock.patch(
        'ddtrace.tracer'
    ) as tracer:
        datadog_agent.get_config = lambda k: agent_config.get(k)
        check.check({})

        if called:
            tracer.trace.assert_called_once_with('check', service='dummy-integration', resource='check')
        else:
            tracer.trace.assert_not_called()
        aggregator.assert_metric('dummy.metric', 10, count=1)


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
                    mock.call('__init__', resource='__init__', service='dummy-integration'),
                    mock.call('check', resource='check', service='dummy-integration'),
                ],
                any_order=True,
            )
        else:
            tracer.trace.assert_not_called()
