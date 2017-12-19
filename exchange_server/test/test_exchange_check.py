# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import copy

# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest


INSTANCE = {
}

INSTANCE_METRICS = [
    'exchange.adaccess_domain_controllers.ldap_read',
    'exchange.adaccess_domain_controllers.ldap_search',
]

@attr('windows')
@attr(requires='exchange_check')
class ExchangeCheckTest(AgentCheckTest):
    CHECK_NAME = 'exchange_check'

    def test_basic_check(self):
        instance = copy.deepcopy(INSTANCE)
        self.run_check({'instances': [instance]})

        for metric in INSTANCE_METRICS:
            self.assertMetric(metric, tags=None, count=1)

        self.coverage_report()
