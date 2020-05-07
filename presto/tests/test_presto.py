# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import prestodb
import pytest

from datadog_checks.dev.jmx import JVM_E2E_METRICS
from datadog_checks.dev.utils import get_metadata_metrics

from .common import METRICS


def make_query():
    # make a query so that all metrics are emitted in the e2e test
    conn = prestodb.dbapi.connect(host='localhost', port=8080, user='test', catalog='test', schema='test',)
    cur = conn.cursor()
    cur.execute('SELECT * FROM system.runtime.nodes')
    cur.fetchall()


@pytest.mark.e2e
def test(dd_agent_check):
    #make_query()

    instance = {}
    aggregator = dd_agent_check(instance, rate=True)

    for metric in METRICS + JVM_E2E_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=JVM_E2E_METRICS)
