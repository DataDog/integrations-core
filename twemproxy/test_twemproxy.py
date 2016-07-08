# stdlib
from nose.plugins.attrib import attr

# 3p

# project
from tests.checks.common import AgentCheckTest


instance = {
    'host': 'localhost',
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
    'forward_error'
])

SERVER_STATS = set([
    'in_queue',
    'out_queue',
    'server_connections',
    'server_err',
    'server_timedout',
    'server_eof'
])


# NOTE: Feel free to declare multiple test classes if needed

@attr(requires='twemproxy', mock=False)  # set mock to True if appropriate
class TestTwemproxy(AgentCheckTest):
    """Basic Test for twemproxy integration."""
    CHECK_NAME = 'twemproxy'

    def test_check(self):
        """
        Testing Twemproxy check.
        """
        self.config = {
            "instances": [instance]
        }

        # self.load_check({}, {})

        # run your actual tests...
        self.run_check(self.config)

        for stat in GLOBAL_STATS:
            self.assertMetric("twemproxy.{}".format(stat), count=1)
        for stat in POOL_STATS:
            self.assertMetric("twemproxy.{}".format(stat), count=1)
        for stat in SERVER_STATS:
            self.assertMetric("twemproxy.{}".format(stat), count=1)

        # Raises when COVERAGE=true and coverage < 100%
        self.coverage_report()
