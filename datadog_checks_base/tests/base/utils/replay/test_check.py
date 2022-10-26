# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.testing import requires_py3

pytestmark = [requires_py3]


class ReplayCheck(AgentCheck):
    __NAMESPACE__ = 'replay'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.redirecting = not self.instance.get('process_isolation', self.init_config.get('process_isolation', False))
        self.tags = ['redirecting:{}'.format(str(self.redirecting).lower())]
        self.tags.extend(self.instance.get('tags', []))
        self.tags.extend(self.init_config.get('tags', []))

        self.check_initializations.append(self.initialize)

    def initialize(self):
        self.gauge('initialize', 0, tags=self.tags)
        self.log.debug('Initializing - %s - %s', self.name, self.check_id)

    def check(self, _):
        self.gauge('metric', 0, tags=self.tags)
        self.service_check('sc', ServiceCheck.OK if self.redirecting else ServiceCheck.CRITICAL, tags=self.tags)


@pytest.mark.parametrize(
    'init_config, instance_config',
    [
        pytest.param(
            {'tags': ['bar:baz']}, {'process_isolation': True, 'tags': ['foo:bar']}, id='Instance-level config'
        ),
        pytest.param({'tags': ['bar:baz'], 'process_isolation': True}, {'tags': ['foo:bar']}, id='Init-level config'),
    ],
)
def test_replay_all(caplog, dd_run_check, aggregator, datadog_agent, init_config, instance_config):
    datadog_agent._config['log_level'] = 'debug'

    check = ReplayCheck('replay', init_config, [instance_config])
    check.check_id = 'test:123'

    with caplog.at_level(logging.DEBUG):
        dd_run_check(check)

    expected_tags = ['redirecting:true', 'bar:baz', 'foo:bar']

    aggregator.assert_metric('replay.initialize', 0, count=1, tags=expected_tags)
    aggregator.assert_metric('replay.metric', 0, count=1, tags=expected_tags)
    aggregator.assert_service_check('replay.sc', ServiceCheck.OK, count=1, tags=expected_tags)
    aggregator.assert_all_metrics_covered()

    expected_message = 'Initializing - replay - test:123'
    for _, level, message in caplog.record_tuples:
        if level == logging.DEBUG and message == expected_message:
            break
    else:
        raise AssertionError('Expected DEBUG log with message: {}'.format(expected_message))
