# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

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

@attr(requires='gunicorn')
class TestGunicorn(AgentCheckTest):
    """Basic Test for gunicorn integration."""
    CHECK_NAME = 'gunicorn'

    def test_check(self):
        """
        Testing Gunicorn check.
        """
        self.run_check({'instances': [{'proc_name': 'dd-test-gunicorn'}]})

        self.assertMetric("gunicorn.workers", tags=['app:dd-test-gunicorn', 'state:idle'], at_least=0)
        self.assertMetric("gunicorn.workers", tags=['app:dd-test-gunicorn', 'state:working'], at_least=0)

        self.assertServiceCheck("gunicorn.is_running", count=1)

        self.coverage_report()
