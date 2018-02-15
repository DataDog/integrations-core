# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from nose.plugins.attrib import attr

# 3p

# project
from tests.checks.common import AgentCheckTest

# NOTE: Feel free to declare multiple test classes if needed

@attr(requires='linkerd')
class TestLinkerd(AgentCheckTest):
    """Basic Test for linkerd integration."""
    CHECK_NAME = 'linkerd'

    LINKERD_CONFIG = [{
        'prometheus_endpoint': "http://localhost:9990/admin/metrics/prometheus",
    }]

    def test_check(self):
        config = {
            'instances': self.LINKERD_CONFIG,
            'init_config': {
                'linkerd_prometheus_prefix': 'dd_linkerd_'
            }
        }

        self.run_check(config)

        self.assertMetric("linkerd.jvm.start_time", count=1)
