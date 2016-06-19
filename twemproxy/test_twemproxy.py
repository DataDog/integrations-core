# stdlib
from nose.plugins.attrib import attr

# 3p

# project
from tests.checks.common import AgentCheckTest


instance = {
    'host': 'localhost',
    'port': 26379,
    'password': 'datadog-is-devops-best-friend'
}


# NOTE: Feel free to declare multiple test classes if needed

@attr(requires='twemproxy', mock=False)  # set mock to True if appropriate
class TestTwemproxy(AgentCheckTest):
    """Basic Test for twemproxy integration."""
    CHECK_NAME = 'twemproxy'

    def test_check(self):
        """
        Testing Twemproxy check.
        """
        self.load_check({}, {})

        # run your actual tests...

        self.assertTrue(True)
        # Raises when COVERAGE=true and coverage < 100%
        self.coverage_report()
