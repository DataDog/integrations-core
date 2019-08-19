# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.mapr import MaprCheck

from .common import KAFKA_METRIC


@pytest.mark.unit
def test_whitelist(instance):
    instance['whitelist'] = ['fs.*', 'db.*']
    check = MaprCheck('mapr', {}, {}, [instance])

    assert check.should_collect_metric('mapr.fs.read_cachemisses')
    assert check.should_collect_metric('mapr.db.get_currpcs')
    assert not check.should_collect_metric('mapr.cache.misses_largefile')


@pytest.mark.unit
def test_submit_gauge(instance, aggregator):
    check = MaprCheck('mapr', {}, {}, [instance])
    check.submit_metric(KAFKA_METRIC, [])

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
def test_submit_gauge_additional_tags(instance, aggregator):
    check = MaprCheck('mapr', {}, {}, [instance])
    check.submit_metric(KAFKA_METRIC, ['foo:bar', 'baz:biz'])

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
def test_submit_bucket(instance, aggregator):
    kafka_metric = {
        "metric": "mapr.db.table.latency",
        "buckets": {"2,5": 10, "5,10": 21},
        "tags": {
            "table_fid": "2070.36.262534",
            "table_path": "/var/mapr/mapr.monitoring/tsdb",
            "noindex": "//primary",
            "rpc_type": "put",
            "fqdn": "mapr-lab-2-ghs6.c.datadog-integrations-lab.internal",
            "clusterid": "7616098736519857348",
            "clustername": "demo",
        },
    }
    check = MaprCheck('mapr', {}, {}, [instance])
    check.submit_metric(kafka_metric, [])
    expected_tags = [
        "clusterid:7616098736519857348",
        "clustername:demo",
        "fqdn:mapr-lab-2-ghs6.c.datadog-integrations-lab.internal",
        "noindex://primary",
        "rpc_type:put",
        "table_fid:2070.36.262534",
        "table_path:/var/mapr/mapr.monitoring/tsdb",
    ]

    aggregator.assert_histogram_bucket('mapr.db.table.latency', 10, 2, 5, True, 'stubbed.hostname', expected_tags)
    aggregator.assert_histogram_bucket('mapr.db.table.latency', 21, 5, 10, True, 'stubbed.hostname', expected_tags)
    aggregator.assert_all_metrics_covered()  # No metrics submitted


def test_check(aggregator, instance):
    check = MaprCheck('mapr', {}, {}, [instance])
    check.check(instance)

    aggregator.assert_all_metrics_covered()
