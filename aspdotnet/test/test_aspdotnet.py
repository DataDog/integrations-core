# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from nose.plugins.attrib import attr

# 3p

# project
from tests.checks.common import AgentCheckTest


# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest
from checks import AgentCheck


MINIMAL_INSTANCE = {
    'host': '.',
}

INSTANCE_WITH_TAGS = {
    'host': '.',
    'tags': ['tag1', 'another:tag']
}


@attr('windows')
@attr(requires='aspdotnet')
class ASPDotNetTest(AgentCheckTest):
    CHECK_NAME = 'aspdotnet'

    # these metrics are single-instance, so they won't have per-instance tags
    ASP_METRICS = (
        "aspdotnet.application_restarts",
        "aspdotnet.worker_process_restarts",
        "aspdotnet.request.wait_time",
    )

    # these metrics are multi-instance.
    ASP_APP_METRICS = (
        # ASP.Net Applications
        "aspdotnet.applications.requests.in_queue",
        "aspdotnet.applications.requests.executing",
        "aspdotnet.applications.requests.persec",
        "aspdotnet.applications.forms_authentication.failure",
        "aspdotnet.applications.forms_authentication.successes",
    )

    def test_basic_check(self):
        self.run_check_twice({'instances': [MINIMAL_INSTANCE]})

        for metric in self.ASP_METRICS:
            self.assertMetric(metric, tags=None, count=1)

        for metric in self.ASP_APP_METRICS:
            self.assertMetric(metric, tags=["instance:__Total__"], count=1)

        self.coverage_report()

    def test_with_tags(self):
        self.run_check_twice({'instances': [INSTANCE_WITH_TAGS]})

        for metric in self.ASP_METRICS:
            self.assertMetric(metric, tags=['tag1', 'another:tag'], count=1)

        for metric in self.ASP_APP_METRICS:
            self.assertMetric(metric, tags=['tag1', 'another:tag', 'instance:__Total__'], count=1)

        self.coverage_report()