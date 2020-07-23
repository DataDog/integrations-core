# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import iteritems

from datadog_checks.mapr import MaprCheck
from datadog_checks.mapr.common import ALLOWED_METRICS, COUNT_METRICS, GAUGE_METRICS, MONOTONIC_COUNTER_METRICS
from datadog_checks.mapr.utils import get_stream_id_for_topic

from .common import DISTRIBUTION_METRIC, KAFKA_METRIC, METRICS_IN_FIXTURE, STREAM_ID_FIXTURE


@pytest.mark.unit
def test_metrics_constants():
    """Make sure those sets have a two-by-two empty intersection"""
    for m in ALLOWED_METRICS:
        total = 0
        if m in GAUGE_METRICS:
            total += 1
        elif m in COUNT_METRICS:
            total += 1
        elif m in MONOTONIC_COUNTER_METRICS:
            total += 1

        assert total == 1


@pytest.mark.unit
def test_get_stream_id():
    for (text, rng), value in iteritems(STREAM_ID_FIXTURE):
        assert get_stream_id_for_topic(text, rng=rng) == value


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_whitelist(instance):
    instance['metric_whitelist'] = [r'mapr\.fs.*', r'mapr\.db.*']
    check = MaprCheck('mapr', {}, [instance])

    for m in ALLOWED_METRICS:
        if m.startswith('mapr.fs') or m.startswith('mapr.db'):
            assert check.should_collect_metric(m)
        else:
            assert not check.should_collect_metric(m)


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_submit_gauge(instance, aggregator):
    check = MaprCheck('mapr', {}, [instance])
    check.submit_metric(KAFKA_METRIC)

    aggregator.assert_metric(
        'mapr.process.context_switch_involuntary',
        value=6308,
        tags=[
            'clustername:demo',
            'process_name:apiserver',
            'clusterid:7616098736519857348',
            'fqdn:mapr-lab-2-ghs6.c.datadog-integrations-lab.internal',
        ],
    )


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_submit_gauge_additional_tags(instance, aggregator):
    instance['tags'] = ["foo:bar", "baz:biz"]
    check = MaprCheck('mapr', {}, [instance])
    check.submit_metric(KAFKA_METRIC)

    aggregator.assert_metric(
        'mapr.process.context_switch_involuntary',
        tags=[
            'clustername:demo',
            'process_name:apiserver',
            'clusterid:7616098736519857348',
            'fqdn:mapr-lab-2-ghs6.c.datadog-integrations-lab.internal',
            'foo:bar',
            'baz:biz',
        ],
    )


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_submit_bucket(instance, aggregator):
    check = MaprCheck('mapr', {}, [instance])
    check.submit_metric(DISTRIBUTION_METRIC)
    expected_tags = [
        "clusterid:7616098736519857348",
        "clustername:demo",
        "fqdn:mapr-lab-2-dhk4.c.datadog-integrations-lab.internal",
        "noindex://primary",
        "rpc_type:put",
        "table_fid:2070.42.262546",
        "table_path:/var/mapr/mapr.monitoring/tsdb-meta",
    ]
    aggregator.assert_histogram_bucket('mapr.db.table.latency', 21, 2, 5, True, 'stubbed.hostname', expected_tags)
    aggregator.assert_histogram_bucket('mapr.db.table.latency', 11, 5, 10, True, 'stubbed.hostname', expected_tags)
    aggregator.assert_all_metrics_covered()  # No metrics submitted


@pytest.mark.usefixtures("mock_getconnection")
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_check(aggregator, instance):
    check = MaprCheck('mapr', {}, [instance])
    check.check(instance)

    for m in METRICS_IN_FIXTURE:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
