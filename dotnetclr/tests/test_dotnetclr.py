# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
import pytest
from datadog_checks.stubs import aggregator
from datadog_checks.dotnetclr import DotnetclrCheck
from datadog_checks.dotnetclr.dotnetclr import DEFAULT_COUNTERS

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


CHECK_NAME = 'active_directory'

INSTANCES = [
    '_Global_',
    'Microsoft.Exchange.Search.Service',
    'UMWorkerProcess',
    'umservice',
    'w3wp',
    'Microsoft.Exchange.Store.Worker',
    'Microsoft.Exchange.EdgeSyncSvc',
    'MSExchangeDelivery',
    'MSExchangeFrontendTransport',
    'Microsoft.Exchange.Store.Service',
    'EdgeTransport',
    'MSExchangeTransport',
    'Microsoft.Exchange.UM.CallRouter',
    'MSExchangeTransportLogSearch',
    'MSExchangeThrottling',
    'MSExchangeHMWorker',
    'MSExchangeSubmission',
    'Microsoft.Exchange.ServiceHost',
    'Microsoft.Exchange.RpcClientAccess.Service',
    'noderunner',
    'msexchangerepl',
    'MSExchangeMailboxReplication',
    'MSExchangeMailboxAssistants',
    'ForefrontActiveDirectoryConnector',
    'Microsoft.Exchange.AntispamUpdateSvc',
    'Ec2Config',
    'Microsoft.Exchange.Directory.TopologyService',
    'WMSvc',
    'MSExchangeHMHost',
    'Microsoft.Exchange.Diagnostics.Service',
    'hostcontrollerservice',
    'Microsoft.ActiveDirectory.WebServices',
]


# flake8 then says this is a redefinition of unused, which it's not.
@pytest.mark.usefixtures("pdh_mocks_fixture")  # noqa: F811
def test_basic_check(Aggregator, pdh_mocks_fixture):
    initialize_pdh_tests()
    instance = MINIMAL_INSTANCE
    c = DotnetclrCheck(CHECK_NAME, {}, {}, [instance])
    c.check(instance)

    for metric_def in DEFAULT_COUNTERS:
        metric = metric_def[3]
        for inst in INSTANCES:
            Aggregator.assert_metric(metric, tags=["instance:%s" % inst], count=1)

    assert Aggregator.metrics_asserted_pct == 100.0
