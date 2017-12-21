# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import os
from mock import MagicMock
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest


instance = {
    'prometheus_endpoint': 'http://localhost:10055/metrics',
}


@attr(requires='kube_dns')
class TestKubeDNS(AgentCheckTest):
    """Basic Test for kube_dns integration."""
    CHECK_NAME = 'kube_dns'
    NAMESPACE = 'kubedns'
    METRICS = [
        NAMESPACE + '.response_size.bytes.count',
        NAMESPACE + '.response_size.bytes.sum',
        NAMESPACE + '.request_duration.seconds.count',
        NAMESPACE + '.request_duration.seconds.sum',
        NAMESPACE + '.request_count',
        NAMESPACE + '.error_count',
        NAMESPACE + '.cachemiss_count',
    ]

    def test_check(self):
        """
        Testing kube_dns check.
        """
        content_type = 'text/plain; version=0.0.4'
        f_name = os.path.join(os.path.dirname(__file__), 'ci', 'metrics.txt')
        with open(f_name, 'r') as f:
            bin_data = f.read()

        mocks = {
            'poll': MagicMock(return_value=[content_type, bin_data])
        }

        self.run_check({'instances': [instance]}, mocks=mocks)
        for metric in self.METRICS:
            self.assertMetric(metric)

        self.coverage_report()
