# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from nose.plugins.attrib import attr

# 3p

# project
from shared.test.common import AgentCheckTest


instance = {
    'host': 'localhost',
    'port': 8126,
}

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
        self.run_check(instance)
        # There shouldn't be any metrics collected in a simple run.
        self.coverage_report()
