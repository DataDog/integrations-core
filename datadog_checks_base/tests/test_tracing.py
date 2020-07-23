# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.tracing import traced


class DummyCheck(AgentCheck):
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
        'datadog_checks.base.utils.tracing.tracer'
    ) as tracer:
        datadog_agent.get_config = lambda k: agent_config.get(k)
        check.check({})

        if called:
            tracer.trace.assert_called_once_with('dummy', service='integrations-tracing', resource='check')
        else:
            tracer.trace.assert_not_called()
        aggregator.assert_metric('dummy.metric', 10, count=1)
