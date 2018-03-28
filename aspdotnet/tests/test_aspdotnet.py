# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from datadog_checks.stubs import aggregator as _aggregator
from datadog_checks.aspdotnet import AspdotnetCheck

MINIMAL_INSTANCE = {
    'host': '.',
}

INSTANCE_WITH_TAGS = {
    'host': '.',
    'tags': ['tag1', 'another:tag']
}


@pytest.fixture
def aggregator():
    _aggregator.reset()
    return _aggregator


class ASPDotNetTest:
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
        instance = MINIMAL_INSTANCE
        c = AspdotnetCheck(self.CHECK_NAME, {}, {}, [instance])
        c.check(instance)

        for metric in self.ASP_METRICS:
            aggregator.assert_metric(metric, tags=None, count=1)

        for metric in self.ASP_APP_METRICS:
            aggregator.assert_metric(metric, tags=["instance:__Total__"], count=1)

        assert aggregator.metrics_asserted_pct == 100.0

    def test_with_tags(self):
        instance = INSTANCE_WITH_TAGS
        c = AspdotnetCheck(self.CHECK_NAME, {}, {}, [instance])
        c.check(instance)

        for metric in self.ASP_METRICS:
            aggregator.assert_metric(metric, tags=['tag1', 'another:tag'], count=1)

        for metric in self.ASP_APP_METRICS:
            aggregator.assert_metric(metric, tags=['tag1', 'another:tag', 'instance:__Total__'], count=1)

        assert aggregator.metrics_asserted_pct == 100.0
