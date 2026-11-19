# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import contextlib
import io
import json
import tempfile
from pathlib import Path

from asset_metrics import extract_metrics, load_metadata_types, main, scan_assets


def _dashboard(query: str) -> dict:
    return {"widgets": [{"definition": {"requests": [{"queries": [{"data_source": "metrics", "query": query}]}]}}]}


def _legacy_dashboard(query: str) -> dict:
    return {"widgets": [{"definition": {"type": "timeseries", "requests": [{"q": query}]}}]}


def test_dotted_metric_with_and_without_aggregator():
    assert extract_metrics(_dashboard("avg:redis.mem.used{$scope} by {host}")) == {"redis.mem.used"}
    assert extract_metrics(_dashboard("postgresql.rows_inserted{$scope}")) == {"postgresql.rows_inserted"}


def test_dotless_metric_after_aggregator():
    monitor = {"type": "query alert", "query": "sum(last_5m):sum:otelcol_receiver_refused_spans{*} by {host} > 0"}
    assert extract_metrics(monitor) == {"otelcol_receiver_refused_spans"}


def test_dotless_metric_after_every_aggregator():
    # One entry per AGG alternative, so dropping any of them fails here.
    aggregators = ("avg", "sum", "min", "max", "count", "p50", "p75", "p90", "p95", "p99", "p99.9", "p99.99")
    for agg in aggregators:
        monitor = {"type": "query alert", "query": f"{agg}:otelcol_exporter_queue_size{{*}} > 10"}
        assert extract_metrics(monitor) == {"otelcol_exporter_queue_size"}, agg


def test_dotless_tokens_without_aggregator_are_ignored():
    assert extract_metrics(_dashboard("a / b")) == set()
    assert extract_metrics(_dashboard("otelcol_bare{*}")) == set()
    assert extract_metrics(_dashboard("avg:redis.mem.used{$scope} by {host,db}")) == {"redis.mem.used"}


def test_undocumented_aggregators_are_not_prefixes():
    for agg in ("last", "pct", "percentile", "median", "stddev", "normalize", "weight"):
        monitor = {"type": "query alert", "query": f"{agg}:otelcol_exporter_queue_size{{*}} > 10"}
        assert extract_metrics(monitor) == set(), agg


def test_aggregator_inside_a_longer_token_is_ignored():
    for prefix in ("top5", "checksum", "mysum", "foo_avg"):
        monitor = {"type": "query alert", "query": f"{prefix}:otelcol_exporter_queue_size{{*}} > 10"}
        assert extract_metrics(monitor) == set(), prefix


def test_dotted_metric_inside_a_longer_token_is_ignored():
    for query in ("9redis.mem{*}", "1.5redis.mem{*}", "$env.value{*}"):
        assert extract_metrics(_dashboard(query)) == set(), query


def test_metric_after_operators():
    cases = {
        "avg(last_5m):avg:otelcol_queue{*} > 1": {"otelcol_queue"},
        "sum:system.mem.total{*}-sum:system.mem.usable{*}": {"system.mem.total", "system.mem.usable"},
        "-avg:redis.mem.used{*}": {"redis.mem.used"},
        "100*sum:redis.net.clients{*}": {"redis.net.clients"},
        "sum:redis.a{*}/sum:redis.b{*}+sum:redis.c{*}": {"redis.a", "redis.b", "redis.c"},
        "sum:redis.a{*},sum:redis.b{*}": {"redis.a", "redis.b"},
    }
    for query, expected in cases.items():
        assert extract_metrics(_dashboard(query)) == expected, query


def test_uppercase_metric_names_keep_their_case():
    # clickhouse ships CamelCase segments that metadata.csv declares verbatim.
    query = "sum:clickhouse.events.SelectQuery.count{$scope}.as_count()"
    assert extract_metrics(_dashboard(query)) == {"clickhouse.events.SelectQuery.count"}


def test_metrics_inside_functions_and_arithmetic():
    queries = {
        "top(avg:twistlock.images.cve.details{*} by {severity}, 10, 'mean', 'desc')": {"twistlock.images.cve.details"},
        "per_second(sum:nginx.net.request{$host}.as_count()).rollup(sum, 60)": {"nginx.net.request"},
        "timeshift(avg:redis.net.clients{*}, -3600)": {"redis.net.clients"},
        "100*sum:presto.done{*}/(sum:presto.ok{*}+sum:presto.failed{*})": {"presto.done", "presto.ok", "presto.failed"},
        "system.load.1{$scope}, system.load.15{$scope}": {"system.load.1", "system.load.15"},
        "count(v: v>=0):data_streams.latency{type:kafka}": {"data_streams.latency"},
        "avg:redis.mem.used {*}": {"redis.mem.used"},
    }
    for query, expected in queries.items():
        assert extract_metrics(_dashboard(query)) == expected, query


def test_template_variables_are_not_metrics():
    query = "sum:snmp.devices_monitored{agent_host:$Agent_Hostname.value,$openai.user.api_key}"
    assert extract_metrics(_dashboard(query)) == {"snmp.devices_monitored"}


def test_legacy_q_requests_are_read():
    assert extract_metrics(_legacy_dashboard("avg:redis.mem.used{*} by {host}")) == {"redis.mem.used"}
    hostmap = {"requests": {"fill": {"q": "avg:system.cpu.user{*} by {host}"}, "size": {"q": "avg:system.mem.used{*}"}}}
    assert extract_metrics(hostmap) == {"system.cpu.user", "system.mem.used"}
    # `type` only gates `query`; a legacy `q` next to a `type` is still a metric query.
    assert extract_metrics({"type": "log alert", "q": "avg:redis.mem.used{*}"}) == {"redis.mem.used"}


def test_only_metric_monitor_types_are_read():
    query = "avg(last_5m):avg:redis.mem.used{*} > 1"
    for monitor_type in ("query alert", "metric alert"):
        assert extract_metrics({"type": monitor_type, "query": query}) == {"redis.mem.used"}, monitor_type
    for monitor_type in ("log alert", "service check", "event-v2 alert", "composite", "slo alert"):
        assert extract_metrics({"type": monitor_type, "query": query}) == set(), monitor_type


def test_non_metric_widgets_are_ignored():
    for widget_type in ("log_stream", "event_stream", "manage_status"):
        assert extract_metrics({"type": widget_type, "query": "avg:svc.metric{*}"}) == set(), widget_type


def test_non_metric_queries_are_ignored():
    logs = {"widgets": [{"definition": {"requests": [{"queries": [{"data_source": "logs", "query": "sum:svc{*}"}]}]}}]}
    assert extract_metrics(logs) == set()


def test_queries_nested_under_non_metric_data_source_are_ignored():
    logs = {"data_source": "logs", "compute": {"aggregation": "count"}, "search": {"query": "avg:svc.metric{*}"}}
    assert extract_metrics({"queries": [logs]}) == set()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_scan_assets_skips_malformed_json():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        dashboards = root / "assets" / "dashboards"
        _write(dashboards / "b.json", json.dumps(_dashboard("avg:redis.mem.used{*}")))
        _write(dashboards / "a.json", json.dumps(_legacy_dashboard("avg:redis.net.clients{*}")))
        _write(dashboards / "broken.json", "{not json")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            files, metrics = scan_assets(dashboards, root)
    assert files == ["assets/dashboards/a.json", "assets/dashboards/b.json"]
    assert metrics == {"redis.mem.used", "redis.net.clients"}
    assert "broken.json" in stderr.getvalue()


def test_load_metadata_types():
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "metadata.csv"
        assert load_metadata_types(csv_path) == {}
        _write(csv_path, "metric_name,metric_type\n redis.mem.used , gauge \n,count\nredis.net.clients,\n")
        assert load_metadata_types(csv_path) == {"redis.mem.used": "gauge", "redis.net.clients": ""}


def _run_main(argv: list[str]) -> tuple[int, str]:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
        code = main(argv)
    return code, stdout.getvalue()


def test_main_reports_target_and_metadata_join():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "redisdb"
        _write(root / "assets" / "dashboards" / "overview.json", json.dumps(_dashboard("avg:redis.mem.used{*}")))
        monitor = {"definition": {"type": "query alert", "query": "avg(last_5m):max:redis.foo.bar{*} > 1"}}
        _write(root / "assets" / "monitors" / "high.json", json.dumps(monitor))
        _write(root / "metadata.csv", "metric_name,metric_type\nredis.mem.used,gauge\n")
        code, out = _run_main(["asset_metrics.py", str(root)])
    assert code == 0
    assert json.loads(out) == {
        "integration": "redisdb",
        "dashboards": ["assets/dashboards/overview.json"],
        "monitors": ["assets/monitors/high.json"],
        "target": ["redis.foo.bar", "redis.mem.used"],
        "by_source": {"dashboards": ["redis.mem.used"], "monitors": ["redis.foo.bar"]},
        "in_metadata": {"redis.mem.used": "gauge"},
        "missing_from_metadata": ["redis.foo.bar"],
    }


def test_main_without_assets_or_metadata_exits_zero():
    with tempfile.TemporaryDirectory() as tmp:
        code, out = _run_main(["asset_metrics.py", tmp])
    assert code == 0
    report = json.loads(out)
    assert report["target"] == [] and report["dashboards"] == [] and report["missing_from_metadata"] == []


def test_main_rejects_wrong_arguments():
    assert _run_main(["asset_metrics.py"])[0] == 2


if __name__ == "__main__":
    # Runnable without pytest, so the skill can check the extractor before using it.
    for name, test in list(globals().items()):
        if name.startswith("test_") and callable(test):
            test()
    print("asset_metrics tests passed")
