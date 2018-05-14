# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.oracle import Oracle
from .common import (
    CONFIG, TABLESPACE_METRICS
)


def testOracle(aggregator, check, oracle_container):
    check.check(CONFIG)

    for m in TABLESPACE_METRICS + Oracle.SYS_METRICS.values():
        aggregator.assert_metric(m, at_least=1)

    aggregator.assert_service_check(Oracle.SERVICE_CHECK_NAME, tags=['optional:tag1', 'server:localhost:1521'])
    aggregator.assert_all_metrics_covered()
