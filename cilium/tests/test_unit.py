# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.cilium import CiliumCheck
from datadog_checks.cilium.check import CiliumCheckV2
from datadog_checks.cilium.cilium import CiliumCheck as LegacyCiliumCheck
from datadog_checks.cilium.metrics import construct_metrics_config

pytestmark = pytest.mark.unit


def test_construct_metrics_config_strips_total_suffix():
    out = construct_metrics_config({"cilium_drop_count_total": "drop_count.total"})
    assert out == [{"cilium_drop_count": {"name": "drop_count"}}]


def test_construct_metrics_config_strips_counter_suffix():
    out = construct_metrics_config({"cilium_api_counter": "api.counter"})
    assert out == [{"cilium_api": {"name": "api"}}]


def test_construct_metrics_config_passes_through_when_no_suffix():
    out = construct_metrics_config({"cilium_endpoint": "endpoint.count"})
    assert out == [{"cilium_endpoint": {"name": "endpoint.count"}}]


def test_construct_metrics_config_empty_map_returns_empty_list():
    assert construct_metrics_config({}) == []


def test_construct_metrics_config_iterates_every_entry():
    out = construct_metrics_config(
        {
            "a_total": "a.total",
            "b_counter": "b.counter",
            "c": "c",
        }
    )
    assert len(out) == 3
    assert {"a": {"name": "a"}} in out
    assert {"b": {"name": "b"}} in out
    assert {"c": {"name": "c"}} in out


def test_construct_metrics_config_total_substring_not_stripped():
    # "_total" must be a suffix; the substring elsewhere stays intact.
    out = construct_metrics_config({"totally_random": "totally.random"})
    assert out == [{"totally_random": {"name": "totally.random"}}]


def test_construct_metrics_config_counter_substring_not_stripped():
    out = construct_metrics_config({"countermeasure": "countermeasure"})
    assert out == [{"countermeasure": {"name": "countermeasure"}}]


def test_v2_default_metric_limit_is_zero():
    assert CiliumCheckV2.DEFAULT_METRIC_LIMIT == 0


def test_v2_raises_when_neither_endpoint_set():
    check = CiliumCheckV2("cilium", {}, [{}])
    with pytest.raises(ConfigurationError, match="Must specify at least one"):
        check._parse_config()


def test_v2_agent_endpoint_only_builds_one_scraper_pointing_at_agent():
    check = CiliumCheckV2("cilium", {}, [{"agent_endpoint": "http://agent/metrics"}])
    check._parse_config()
    assert len(check.scraper_configs) == 1
    assert check.scraper_configs[0]["openmetrics_endpoint"] == "http://agent/metrics"


def test_v2_operator_endpoint_only_builds_one_scraper_pointing_at_operator():
    check = CiliumCheckV2("cilium", {}, [{"operator_endpoint": "http://op/metrics"}])
    check._parse_config()
    assert len(check.scraper_configs) == 1
    assert check.scraper_configs[0]["openmetrics_endpoint"] == "http://op/metrics"


def test_v2_both_endpoints_build_two_scrapers():
    check = CiliumCheckV2(
        "cilium",
        {},
        [{"agent_endpoint": "http://agent/metrics", "operator_endpoint": "http://op/metrics"}],
    )
    check._parse_config()
    endpoints = sorted(s["openmetrics_endpoint"] for s in check.scraper_configs)
    assert endpoints == ["http://agent/metrics", "http://op/metrics"]


def test_v2_agent_scraper_uses_agent_metrics_not_operator():
    check = CiliumCheckV2("cilium", {}, [{"agent_endpoint": "http://agent/metrics"}])
    check._parse_config()
    metric_keys = {next(iter(m)) for m in check.scraper_configs[0]["metrics"]}
    assert "cilium_drop_count" in metric_keys
    assert not any(name.startswith("cilium_operator_eni_") for name in metric_keys)


def test_v2_operator_scraper_uses_operator_metrics_not_agent():
    check = CiliumCheckV2("cilium", {}, [{"operator_endpoint": "http://op/metrics"}])
    check._parse_config()
    metric_keys = {next(iter(m)) for m in check.scraper_configs[0]["metrics"]}
    assert any(name.startswith("cilium_operator_") for name in metric_keys)
    assert "cilium_drop_count" not in metric_keys


def test_legacy_default_metric_limit_is_zero():
    assert LegacyCiliumCheck.DEFAULT_METRIC_LIMIT == 0


def test_legacy_routes_to_v2_when_use_openmetrics_is_truthy():
    check = CiliumCheck("cilium", {}, [{"agent_endpoint": "http://agent/metrics", "use_openmetrics": True}])
    assert isinstance(check, CiliumCheckV2)


def test_legacy_routes_to_legacy_when_use_openmetrics_is_falsy():
    check = CiliumCheck("cilium", {}, [{"agent_endpoint": "http://agent/metrics", "use_openmetrics": False}])
    assert not isinstance(check, CiliumCheckV2)


def test_legacy_default_use_openmetrics_routes_to_legacy():
    # When the key is absent, the get() default must be False so we stay on legacy.
    check = CiliumCheck("cilium", {}, [{"agent_endpoint": "http://agent/metrics"}])
    assert not isinstance(check, CiliumCheckV2)


def test_legacy_new_picks_first_instance_for_routing_legacy_path():
    check = CiliumCheck(
        "cilium",
        {},
        [
            {"agent_endpoint": "http://agent/metrics", "use_openmetrics": False},
            {"agent_endpoint": "http://agent2/metrics", "use_openmetrics": True},
        ],
    )
    assert not isinstance(check, CiliumCheckV2)


def test_legacy_new_picks_first_instance_for_routing_v2_path():
    check = CiliumCheck(
        "cilium",
        {},
        [
            {"agent_endpoint": "http://agent/metrics", "use_openmetrics": True},
            {"agent_endpoint": "http://agent2/metrics", "use_openmetrics": False},
        ],
    )
    assert isinstance(check, CiliumCheckV2)


def test_legacy_raises_when_both_endpoints_set():
    with pytest.raises(ConfigurationError, match="Only one endpoint needs to be specified"):
        CiliumCheck(
            "cilium",
            {},
            [{"agent_endpoint": "http://agent/metrics", "operator_endpoint": "http://op/metrics"}],
        )


def test_legacy_raises_when_neither_endpoint_set():
    with pytest.raises(ConfigurationError, match="Must provide at least one endpoint"):
        CiliumCheck("cilium", {}, [{}])


def test_legacy_init_uses_first_instance_for_endpoint_choice():
    check = CiliumCheck(
        "cilium",
        {},
        [
            {"agent_endpoint": "http://first/metrics"},
            {"agent_endpoint": "http://second/metrics"},
        ],
    )
    assert check.instance["prometheus_url"] == "http://first/metrics"


def test_legacy_operator_endpoint_selects_operator_metric_set():
    check = CiliumCheck("cilium", {}, [{"operator_endpoint": "http://op/metrics"}])
    assert check.instance["prometheus_url"] == "http://op/metrics"
    rendered = repr(check.instance["metrics"])
    assert "cilium_operator_process_cpu_seconds_total" in rendered


def test_legacy_agent_endpoint_selects_agent_metric_set():
    check = CiliumCheck("cilium", {}, [{"agent_endpoint": "http://agent/metrics"}])
    assert check.instance["prometheus_url"] == "http://agent/metrics"
    rendered = repr(check.instance["metrics"])
    assert "cilium_drop_count_total" in rendered
    assert "cilium_operator_eni_available" not in rendered


def test_legacy_default_prometheus_timeout_is_10():
    check = CiliumCheck("cilium", {}, [{"agent_endpoint": "http://agent/metrics"}])
    assert check.instance["prometheus_timeout"] == 10


def test_legacy_custom_timeout_passes_through():
    check = CiliumCheck("cilium", {}, [{"agent_endpoint": "http://agent/metrics", "timeout": 42}])
    assert check.instance["prometheus_timeout"] == 42


def test_legacy_namespace_is_cilium():
    check = CiliumCheck("cilium", {}, [{"agent_endpoint": "http://agent/metrics"}])
    assert check.instance["namespace"] == "cilium"


def test_legacy_metadata_metric_name_is_cilium_version():
    check = CiliumCheck("cilium", {}, [{"agent_endpoint": "http://agent/metrics"}])
    assert check.instance["metadata_metric_name"] == "cilium_version"
