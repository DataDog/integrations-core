# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import pytest
from datadog_checks.stubs import aggregator
from datadog_checks.aspdotnet import AspdotnetCheck

# for reasons unknown, flake8 says that pdh_mocks_fixture is unused, even though
# it's used below.  noqa to suppress that error.
from datadog_test_libs.win.pdh_mocks import pdh_mocks_fixture, initialize_pdh_tests  # noqa: F401

HERE = os.path.abspath(os.path.dirname(__file__))
MINIMAL_INSTANCE = {
    'host': '.',
}

INSTANCE_WITH_TAGS = {
    'host': '.',
    'tags': ['tag1', 'another:tag']
}


@pytest.fixture
def Aggregator():
    aggregator.reset()
    return aggregator


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

ASP_APP_INSTANCES = (
    "__Total__",
    "_LM_W3SVC_1_ROOT_owa_Calendar",
    "_LM_W3SVC_2_ROOT_Microsoft-Server-ActiveSync",
    "_LM_W3SVC_1_ROOT_Microsoft-Server-ActiveSync",
    "_LM_W3SVC_2_ROOT_ecp",
    "_LM_W3SVC_1_ROOT_ecp",
    "_LM_W3SVC_2_ROOT_Rpc",
    "_LM_W3SVC_1_ROOT_Rpc",
    "_LM_W3SVC_2_ROOT_Autodiscover",
    "_LM_W3SVC_1_ROOT_EWS",
    "_LM_W3SVC_2_ROOT_EWS",
    "_LM_W3SVC_1_ROOT_Autodiscover",
    "_LM_W3SVC_1_ROOT_PowerShell",
    "_LM_W3SVC_2_ROOT_PowerShell",
    "_LM_W3SVC_1_ROOT_OAB",
    "_LM_W3SVC_2_ROOT_owa",
    "_LM_W3SVC_1_ROOT_owa",
)


# flake8 then says this is a redefinition of unused, which it's not.
@pytest.mark.usefixtures("pdh_mocks_fixture")  # noqa: F811
def test_basic_check(Aggregator, pdh_mocks_fixture):
    initialize_pdh_tests()
    instance = MINIMAL_INSTANCE
    c = AspdotnetCheck(CHECK_NAME, {}, {}, [instance])
    c.check(instance)

    for metric in ASP_METRICS:
        Aggregator.assert_metric(metric, tags=None, count=1)

    for metric in ASP_APP_METRICS:
        for i in ASP_APP_INSTANCES:
            Aggregator.assert_metric(metric, tags=["instance:%s" % i], count=1)

    assert Aggregator.metrics_asserted_pct == 100.0


# flake8 then says this is a redefinition of unused, which it's not.
def test_with_tags(Aggregator, pdh_mocks_fixture):  # noqa: F811
    initialize_pdh_tests()
    instance = INSTANCE_WITH_TAGS
    c = AspdotnetCheck(CHECK_NAME, {}, {}, [instance])
    c.check(instance)

    for metric in ASP_METRICS:
        Aggregator.assert_metric(metric, tags=['tag1', 'another:tag'], count=1)

    for metric in ASP_APP_METRICS:
        for i in ASP_APP_INSTANCES:
            Aggregator.assert_metric(metric, tags=['tag1', 'another:tag', "instance:%s" % i], count=1)

    assert aggregator.metrics_asserted_pct == 100.0
