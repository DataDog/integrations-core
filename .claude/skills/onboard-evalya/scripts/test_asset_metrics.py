# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from asset_metrics import extract_metrics


def _dashboard(query: str) -> dict:
    return {"widgets": [{"definition": {"requests": [{"queries": [{"data_source": "metrics", "query": query}]}]}}]}


def test_dotted_metric_with_and_without_aggregator():
    assert extract_metrics(_dashboard("avg:redis.mem.used{$scope} by {host}")) == {"redis.mem.used"}
    assert extract_metrics(_dashboard("postgresql.rows_inserted{$scope}")) == {"postgresql.rows_inserted"}


def test_dotless_metric_after_aggregator():
    monitor = {"type": "query alert", "query": "sum(last_5m):sum:otelcol_receiver_refused_spans{*} by {host} > 0"}
    assert extract_metrics(monitor) == {"otelcol_receiver_refused_spans"}


def test_dotless_tokens_without_aggregator_are_ignored():
    assert extract_metrics(_dashboard("avg:redis.mem.used{$scope} by {host}")) == {"redis.mem.used"}
    assert extract_metrics(_dashboard("a / b")) == set()
    assert extract_metrics(_dashboard("otelcol_bare{*}")) == set()


def test_non_metric_queries_are_ignored():
    logs = {"widgets": [{"definition": {"requests": [{"queries": [{"data_source": "logs", "query": "sum:svc{*}"}]}]}}]}
    assert extract_metrics(logs) == set()
