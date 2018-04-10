# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import random

# 3p
from nose.plugins.attrib import attr
from requests import HTTPError

from tests.checks.common import AgentCheckTest, load_check
from utils.containers import hash_mutable

# project
from checks import AgentCheck

MOCK_CONFIG = {
    'init_config': {},
    'instances' : [{
        'url': 'http://localhost:8500',
        'catalog_checks': True,
    }]
}

MOCK_CONFIG_SERVICE_WHITELIST = {
    'init_config': {},
    'instances' : [{
        'url': 'http://localhost:8500',
        'catalog_checks': True,
        'service_whitelist': ['service_{0}'.format(k) for k in range(70)]
    }]
}

MOCK_CONFIG_LEADER_CHECK = {
    'init_config': {},
    'instances' : [{
        'url': 'http://localhost:8500',
        'catalog_checks': True,
        'new_leader_checks': True
    }]
}

MOCK_CONFIG_SELF_LEADER_CHECK = {
    'init_config': {},
    'instances' : [{
        'url': 'http://localhost:8500',
        'catalog_checks': True,
        'self_leader_check': True
    }]
}

MOCK_CONFIG_NETWORK_LATENCY_CHECKS = {
    'init_config': {},
    'instances' : [{
        'url': 'http://localhost:8500',
        'catalog_checks': True,
        'network_latency_checks': True
    }]
}

MOCK_BAD_CONFIG = {
    'init_config': {},
    'instances' : [{ # Multiple instances should cause it to fail
        'url': 'http://localhost:8500',
        'catalog_checks': True,
        'new_leader_checks': True
    }, {
        'url': 'http://localhost:8501',
        'catalog_checks': True,
        'new_leader_checks': True,
        'self_leader_check': True
    }]
}

def _get_random_ip():
    rand_int = int(15 * random.random()) + 10
    return "10.0.2.{0}".format(rand_int)


@attr(requires='consul')
class TestIntegrationConsul(AgentCheckTest):
    """Basic Test for consul integration."""
    CHECK_NAME = 'consul'

    METRICS = [
        'consul.catalog.nodes_up',
        'consul.catalog.nodes_passing',
        'consul.catalog.nodes_warning',
        'consul.catalog.nodes_critical',
        'consul.catalog.services_up',
        'consul.catalog.services_passing',
        'consul.catalog.services_warning',
        'consul.catalog.services_critical',
        'consul.net.node.latency.p95',
        'consul.net.node.latency.min',
        'consul.net.node.latency.p25',
        'consul.net.node.latency.median',
        'consul.net.node.latency.max',
        'consul.net.node.latency.max',
        'consul.net.node.latency.p99',
        'consul.net.node.latency.p90',
        'consul.net.node.latency.p75'
    ]

    def simple_integration_test(self):
        """
        Testing Consul Integration
        """

        config = {
            "instances": [{
                'url': 'http://localhost:8500',
                'catalog_checks': True,
                'network_latency_checks': True,
                'new_leader_checks': True,
                'catalog_checks': True,
                'self_leader_check': True,
                'acl_token': 'token'
            }]
        }

        self.run_check(config)

        self.check.log.info(self.metrics)

        for m in self.METRICS:
            self.assertMetric(m, at_least=0)

        self.assertMetric('consul.peers', value=3)

        self.assertServiceCheck('consul.check')
        self.assertServiceCheck('consul.up')

        self.coverage_report()

    def test_acl_forbidden(self):
        """
        Testing Consul Integration
        """

        config = {
            "instances": [{
                'url': 'http://localhost:8500',
                'catalog_checks': True,
                'network_latency_checks': True,
                'new_leader_checks': True,
                'catalog_checks': True,
                'self_leader_check': True,
                'acl_token': 'wrong_token'
            }]
        }
        got_error_403 = False
        try:
            self.run_check(config)
        except HTTPError as e:
            if e.response.status_code == 403:
                got_error_403 = True

        self.assertTrue(got_error_403)
