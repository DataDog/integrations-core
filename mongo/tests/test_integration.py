import json
import os

from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import HERE


def test_integration(instance_custom_queries, aggregator, mock_pymongo, check):
    instance_custom_queries["additional_metrics"] = ["metrics.commands", "tcmalloc", "collection", "top"]
    instance_custom_queries["collections"] = ["foo", "bar"]
    instance_custom_queries["collections_indexes_stats"] = True
    mongo_check = check(instance_custom_queries)
    # Set node as "secondary" initially to trigger an event
    mongo_check._last_state_by_server[mongo_check.clean_server_name] = 2

    mongo_check.check(instance_custom_queries)

    expected_metrics = []
    with open(os.path.join(HERE, "results", "metrics.json"), 'r') as f:
        expected_metrics = json.load(f)

    for metric in expected_metrics:
        aggregator.assert_metric(metric['name'], value=metric['value'], tags=metric['tags'], metric_type=metric['type'])

    aggregator.assert_all_metrics_covered()

    metadata_metrics = get_metadata_metrics()
    aggregator.assert_metrics_using_metadata(
        metadata_metrics,
        exclude=[
            'dd.custom.mongo.aggregate.total',
            'dd.custom.mongo.count',
            'dd.custom.mongo.query_a.amount',
            'dd.custom.mongo.query_a.el',
        ],
        check_metric_type=False,
    )

    # Additionally assert that all metrics in the metadata.csv were submitted in this check run:
    for metric in metadata_metrics:
        assert [
            x for x in expected_metrics if x['name'] == metric
        ], "Metric {} is in metadata.csv but was not submitted.".format(metric)

    assert len(aggregator._service_checks) == 1
    aggregator.assert_service_check(
        'mongodb.can_connect', AgentCheck.OK, tags=['db:test', 'host:localhost', 'port:27017']
    )

    assert len(aggregator._events) == 1
    aggregator.assert_event(
        "MongoDB stubbed.hostname (mongodb://testUser2:*****@localhost:27017/test) "
        "just reported as Primary (PRIMARY) for shard01; it was SECONDARY before.",
        tags=[
            'action:mongo_replset_member_status_change',
            'member_status:PRIMARY',
            'previous_member_status:SECONDARY',
            'replset:shard01',
        ],
    )
