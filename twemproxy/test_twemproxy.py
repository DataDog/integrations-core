# (C) Datadog, Inc. 2016-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from nose.plugins.attrib import attr

# 3p

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest


instance = {
    'host': '127.0.0.1',
    'port': 6222,
}

GLOBAL_STATS = set([
    'curr_connections',
    'total_connections'
])

POOL_STATS = set([
    'client_eof',
    'client_err',
    'client_connections',
    'server_ejects',
    'forward_error',
    'fragments'
])

SERVER_STATS = set([
    'in_queue',
    'out_queue',
    'in_queue_bytes',
    'out_queue_bytes',
    'server_connections',
    'server_timedout',
    'server_err',
    'server_eof',
    'requests',
    'request_bytes',
    'responses',
    'response_bytes',
])


# NOTE: Feel free to declare multiple test classes if needed

@attr(requires='twemproxy', mock=False)  # set mock to True if appropriate
class TestTwemproxy(AgentCheckTest):
    """Basic Test for twemproxy integration."""
    CHECK_NAME = 'twemproxy'
    SC_TAGS = ['host:127.0.0.1', 'port:6222']

    def test_check(self):
        """
        Testing Twemproxy check.
        """
        self.config = {
            "instances": [instance]
        }

        # self.load_check({}, {})

        # run your actual tests...
        self.run_check_twice(self.config)

        for stat in GLOBAL_STATS:
            self.assertMetric("twemproxy.{}".format(stat), at_least=0)
        for stat in POOL_STATS:
            self.assertMetric("twemproxy.{}".format(stat), at_least=1, count=1)
        for stat in SERVER_STATS:
            self.assertMetric("twemproxy.{}".format(stat), at_least=1, count=2)

        # Test service check
        self.assertServiceCheck('twemproxy.can_connect', status=AgentCheck.OK,
                                tags=self.SC_TAGS, count=1)

        # Raises when COVERAGE=true and coverage < 100%
        self.coverage_report()
