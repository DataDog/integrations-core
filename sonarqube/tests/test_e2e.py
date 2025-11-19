# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.constants import ServiceCheck

from .common import CHECK_CONFIG
from .metrics import ALL_METRICS


def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(CHECK_CONFIG, rate=True)

    for metric in ALL_METRICS:
        aggregator.assert_metric(metric)

    jmx_web_instance = CHECK_CONFIG['instances'][0]
    tags = [
        'instance:sonarqube-{}-{}'.format(jmx_web_instance['host'], jmx_web_instance['port']),
        'jmx_server:{}'.format(jmx_web_instance['host']),
    ]
    aggregator.assert_service_check('sonarqube.can_connect', status=ServiceCheck.OK, tags=tags)

    jmx_ce_instance = CHECK_CONFIG['instances'][1]
    tags = [
        'instance:sonarqube-{}-{}'.format(jmx_ce_instance['host'], jmx_ce_instance['port']),
        'jmx_server:{}'.format(jmx_ce_instance['host']),
    ]
    aggregator.assert_service_check('sonarqube.can_connect', status=ServiceCheck.OK, tags=tags)

    web_instance = CHECK_CONFIG['instances'][2]
    tags = ['endpoint:{}'.format(web_instance['web_endpoint'])]
    tags.extend(web_instance['tags'])
    aggregator.assert_service_check('sonarqube.api_access', status=ServiceCheck.OK, tags=tags)
