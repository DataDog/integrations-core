# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Callable

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.ibm_db2 import IbmDb2Check

from . import metrics


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_standard(aggregator, instance):
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check.check(instance)

    _assert_standard(aggregator)


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    _assert_standard(aggregator)


@pytest.mark.e2e
def test_dbm_e2e(dd_agent_check: Callable[..., AggregatorStub], instance: dict):
    """The packaged Agent emits query deltas and FQT with real obfuscation, metadata, and identity."""
    instance.update(
        dbm=True,
        min_collection_interval=0.01,
        query_metrics={'collection_interval': 0.01},
        database_identifier={'template': '$host:$port'},
        custom_queries=[
            {
                'metric_prefix': 'dbm_e2e',
                'query': "SELECT COUNT(*) FROM SYSCAT.TABLES WHERE TABNAME = 'dbm_e2e_literal' AND CARD > 424242",
                'columns': [{'name': 'count', 'type': 'gauge'}],
            }
        ],
    )
    # Execute the workload on every collection, with enough runs for the query-counter baseline and deltas.
    aggregator = dd_agent_check(instance, check_times=3, pause=100, env_vars={'DBM_THREADED_JOB_RUN_SYNC': 'true'})
    rows = [
        (payload, row)
        for payload in aggregator.get_event_platform_events('dbm-metrics')
        for row in payload['ibm_db2_rows']
        if 'SYSCAT.TABLES' in row['query'].upper() and 'CARD >' in row['query'].upper()
    ]
    assert rows
    payload, row = rows[-1]
    assert row['count'] > 0
    assert '?' in row['query']
    assert 'dbm_e2e_literal' not in row['query'].lower()
    assert '424242' not in row['query']
    assert 'SYSCAT.TABLES' in {table.upper() for table in row['dd_tables']}
    assert row['dd_commands'] == ['SELECT']

    samples = [
        event
        for event in aggregator.get_event_platform_events('dbm-samples')
        if event['dbm_type'] == 'fqt' and event['db']['query_signature'] == row['query_signature']
    ]
    assert len(samples) == 1
    sample = samples[0]
    assert sample['db']['statement'] == row['query']
    assert sample['db']['metadata']['tables'] == row['dd_tables']
    assert sample['db']['metadata']['commands'] == row['dd_commands']
    assert sample['db']['instance'] == instance['db']

    for event in (payload, sample):
        assert event['database_instance'] == f"{instance['host']}:{instance['port']}"
    assert sample['host'] == payload['host']


def _assert_standard(aggregator):
    aggregator.assert_service_check('ibm_db2.can_connect', AgentCheck.OK)

    for metric in metrics.STANDARD:
        aggregator.assert_metric_has_tag(metric, 'db:datadog')
        aggregator.assert_metric_has_tag(metric, 'foo:bar')
        aggregator.assert_metric_has_tag_prefix(metric, 'database_hostname:')
        aggregator.assert_metric_has_tag_prefix(metric, 'database_instance:')
    aggregator.assert_all_metrics_covered()
