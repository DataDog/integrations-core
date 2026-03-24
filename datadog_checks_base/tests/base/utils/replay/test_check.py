# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.constants import ServiceCheck


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
        self.log.debug('Metric count: %d', 42)
        self.log.debug('Test log: %s', 'test')
        self.set_external_tags([('myhost', {'src': ['tag:val']})])


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

captured_logs = set((level, message) for _, level, message in caplog.record_tuples)
assert (logging.DEBUG, 'Initializing - replay - test:123'), captured_logs
assert (logging.DEBUG, 'Metric count: 42'), captured_logs

    datadog_agent.assert_external_tags('myhost', {'src': ['tag:val']})
    datadog_agent.assert_external_tags_count(1)


class ReplayCheckBadLog(AgentCheck):
    __NAMESPACE__ = 'replay'

    def check(self, _):
        self.log.debug('TypeError format: %d', 'not_a_number')
        self.log.debug('OverflowError format: %c', 2**32)


def test_replay_log_format_errors(caplog, dd_run_check, datadog_agent):
    datadog_agent._config['log_level'] = 'debug'

    check = ReplayCheckBadLog('replay', {}, [{'process_isolation': True}])
    check.check_id = 'test:123'

    with caplog.at_level(logging.DEBUG):
        dd_run_check(check)

captured_logs = set((level, message) for _, level, message in caplog.record_tuples)
assert (logging.DEBUG, 'TypeError format: %d'), captured_logs
assert (logging.DEBUG, 'OverflowError format: %c'), captured_logs
