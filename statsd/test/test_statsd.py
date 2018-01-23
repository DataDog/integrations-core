# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from nose.plugins.attrib import attr

# 3p

# project
from tests.checks.common import AgentCheckTest


instance = {
    'host': '127.0.0.1',
    'port': 8126,
}

METRICS = [
    'statsd.graphite.flush_length',
    'statsd.messages.last_msg_seen',
    'statsd.counters.count',
    'statsd.graphite.last_exception',
    'statsd.gauges.count',
    'statsd.messages.bad_lines_seen',
    'statsd.graphite.flush_time',
    'statsd.graphite.last_flush',
    'statsd.uptime',
    'statsd.timers.count'
]

SERVICE_CHECKS = [
    'statsd.is_up',
    'statsd.can_connect'
]

# NOTE: Feel free to declare multiple test classes if needed
@attr(requires='statsd')
class TestStatsd(AgentCheckTest):
    """Basic Test for statsd integration."""
    CHECK_NAME = 'statsd'

    # The most complicated part of this is whether or not it's parsing the udp payload correctly
    # for the rest of it, the logic is far less brittle
    def test_simple_run(self):
        """
        Testing Statsd check.
        """
        config = {
            "instances": [instance]
        }
        self.run_check(config)
        for stat in METRICS:
            self.assertMetric(stat, at_least=0)

        for check in SERVICE_CHECKS:
            self.assertServiceCheck(check)

        self.coverage_report()
