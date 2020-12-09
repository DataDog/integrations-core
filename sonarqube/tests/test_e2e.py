# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

from .common import CHECK_CONFIG
from .metrics import ALL_METRICS

pytestmark = [pytest.mark.e2e]


def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(CHECK_CONFIG, rate=True)

    for metric in ALL_METRICS:
        aggregator.assert_metric(metric)

    jmx_instance = CHECK_CONFIG['instances'][0]
    tags = [
        'instance:sonarqube-{}-{}'.format(jmx_instance['host'], jmx_instance['port']),
        'jmx_server:{}'.format(jmx_instance['host']),
    ]
    aggregator.assert_service_check('sonarqube.can_connect', status=ServiceCheck.OK, tags=tags)

    web_instance = CHECK_CONFIG['instances'][1]
    tags = ['endpoint:{}'.format(web_instance['web_endpoint'])]
    tags.extend(web_instance['tags'])
    aggregator.assert_service_check('sonarqube.api_access', status=ServiceCheck.OK, tags=tags)
