# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from types import SimpleNamespace

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kubevirt_handler import KubeVirtHandlerCheck
from datadog_checks.kubevirt_handler import check as check_module

from .conftest import mock_http_responses

pytestmark = pytest.mark.unit

base_tags = [
    "pod_name:virt-handler-some-id",
    "kube_namespace:kubevirt",
]

# Built at runtime so these aren't interned to the same object as the "counter"/"gauge"
# literals in check.py, letting tests observe `==` vs `is` comparisons diverge.
RUNTIME_COUNTER_TYPE = "".join(["c", "o", "u", "n", "t", "e", "r"])
RUNTIME_GAUGE_TYPE = "".join(["g", "a", "u", "g", "e"])


def test_check_collects_metrics(dd_run_check, aggregator, instance, mocker):
    mocker.patch("requests.Session.get", wraps=mock_http_responses)
    check = KubeVirtHandlerCheck("kubevirt_handler", {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric(
        "kubevirt_handler.can_connect",
        1,
        tags=["endpoint:https://127.0.0.1:8443/healthz", *base_tags],
    )

    metric_tags = [
        "kube_namespace:kubevirt",
        "pod_name:virt-handler-some-id",
    ]

    # aggregator.assert_metric_has_tags("kubevirt_handler.info", tags=metric_tags)  # gauge

    aggregator.assert_metric_has_tags(
        "kubevirt_handler.vmi.cpu_system_usage_seconds.count", tags=metric_tags
    )  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.cpu_usage_seconds.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.cpu_user_usage_seconds.count", tags=metric_tags)  # counter

    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.memory_actual_balloon_bytes", tags=metric_tags)  # gauge
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.memory_available_bytes", tags=metric_tags)  # gauge
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.memory_domain_bytes", tags=metric_tags)  # gauge
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.memory_pgmajfault.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.memory_pgminfault.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.memory_resident_bytes", tags=metric_tags)  # gauge
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.memory_swap_in_traffic_bytes", tags=metric_tags)  # gauge
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.memory_swap_out_traffic_bytes", tags=metric_tags)  # gauge
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.memory_unused_bytes", tags=metric_tags)  # gauge
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.memory_usable_bytes", tags=metric_tags)  # gauge

    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.network_receive_bytes.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.network_receive_errors.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.vmi.network_receive_packets_dropped.count", tags=metric_tags
    )  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.network_receive_packets.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.network_transmit_bytes.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.network_transmit_errors.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.vmi.network_transmit_packets_dropped.count", tags=metric_tags
    )  # counter
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.vmi.network_transmit_packets.count", tags=metric_tags
    )  # counter

    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.node_cpu_affinity", tags=metric_tags)  # gauge

    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.storage_flush_requests.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.vmi.storage_flush_times_seconds.count", tags=metric_tags
    )  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.storage_iops_read.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.storage_iops_write.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.vmi.storage_read_times_seconds.count", tags=metric_tags
    )  # counter
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.vmi.storage_read_traffic_bytes.count", tags=metric_tags
    )  # counter
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.vmi.storage_write_times_seconds.count", tags=metric_tags
    )  # counter
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.vmi.storage_write_traffic_bytes.count", tags=metric_tags
    )  # counter

    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.vcpu_delay_seconds.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.vcpu_seconds.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.vcpu_wait_seconds.count", tags=metric_tags)  # counter

    aggregator.assert_metric_has_tags("kubevirt_handler.workqueue.adds.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.workqueue.depth", tags=metric_tags)  # gauge
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.workqueue.longest_running_processor_seconds", tags=metric_tags
    )  # gauge
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.workqueue.queue_duration_seconds.bucket", tags=metric_tags
    )  # histogram
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.workqueue.queue_duration_seconds.sum", tags=metric_tags
    )  # histogram
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.workqueue.queue_duration_seconds.count", tags=metric_tags
    )  # histogram
    aggregator.assert_metric_has_tags("kubevirt_handler.workqueue.retries.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.workqueue.unfinished_work_seconds", tags=metric_tags)  # gauge
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.workqueue.work_duration_seconds.bucket", tags=metric_tags
    )  # histogram
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.workqueue.work_duration_seconds.sum", tags=metric_tags
    )  # histogram
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.workqueue.work_duration_seconds.count", tags=metric_tags
    )  # histogram

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_logs_warning_when_healthz_endpoint_is_missing(dd_run_check, aggregator, instance, mocker, caplog):
    mocker.patch("requests.Session.get", wraps=mock_http_responses)
    del instance["kubevirt_handler_healthz_endpoint"]
    check = KubeVirtHandlerCheck("kubevirt_handler", {}, [instance])
    dd_run_check(check)
    assert (
        "Skipping health check. Please provide a `kubevirt_handler_healthz_endpoint` to ensure the health of the KubeVirt Handler."  # noqa: E501
        in caplog.text
        and "WARNING" in caplog.text
    )


def test_emits_can_connect_one_when_service_is_up(dd_run_check, aggregator, instance, mocker):
    mocker.patch("requests.Session.get", wraps=mock_http_responses)
    check = KubeVirtHandlerCheck("kubevirt_handler", {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        "kubevirt_handler.can_connect",
        1,
        tags=["endpoint:https://127.0.0.1:8443/healthz", *base_tags],
    )


def test_emits_can_connect_zero_when_service_is_down(dd_run_check, aggregator, instance):
    check = KubeVirtHandlerCheck("kubevirt_handler", {}, [instance])
    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_metric(
        "kubevirt_handler.can_connect",
        0,
        tags=["endpoint:https://127.0.0.1:8443/healthz", *base_tags],
    )


def test_version_metadata(instance, dd_run_check, datadog_agent, aggregator, mocker):
    mocker.patch("requests.Session.get", wraps=mock_http_responses)
    check = KubeVirtHandlerCheck("kubevirt_handler", {}, [instance])
    check.check_id = "test:123"
    dd_run_check(check)

    aggregator.assert_metric(
        "kubevirt_handler.can_connect",
        1,
        tags=["endpoint:https://127.0.0.1:8443/healthz", *base_tags],
    )

    version_metadata = {
        "version.scheme": "semver",
        "version.major": "1",
        "version.minor": "2",
        "version.patch": "2",
        "version.raw": "v1.2.2",
    }

    datadog_agent.assert_metadata("test:123", version_metadata)


def test_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at check.py:15 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert KubeVirtHandlerCheck.DEFAULT_METRIC_LIMIT == 0


def test_parse_config_disables_openmetrics_health_service_check(instance):
    # Kills the core/ReplaceFalseWithTrue mutant at check.py:62 (enable_health_service_check False -> True).
    check = KubeVirtHandlerCheck("kubevirt_handler", {}, [instance])
    check._parse_config()
    assert check.scraper_configs[0]["enable_health_service_check"] is False


def test_configure_additional_transformers_registers_wildcard_as_pattern(instance):
    # Kills the core/ReplaceTrueWithFalse mutant at check.py:80 (pattern=True -> pattern=False).
    check = KubeVirtHandlerCheck("kubevirt_handler", {}, [instance])
    check._parse_config()
    check.configure_scrapers()
    check._configure_additional_transformers()
    metric_transformer = check.scrapers[check.kubevirt_handler_metrics_endpoint].metric_transformer
    wildcard_patterns = [
        regex.pattern for regex, _ in metric_transformer.metric_patterns if regex.pattern != "^kubevirt_info$"
    ]
    assert wildcard_patterns == [".*"]


def test_configure_metadata_transformer_extracts_version_parts(instance):
    # Kills the core/NumberReplacer mutants at check.py:88,90,91,92 (kubeversion/version_split index off-by-ones).
    # The "semver" scheme re-parses version_raw itself and ignores part_map, so we capture the part_map
    # argument passed to set_metadata directly rather than asserting on agent-reported metadata.
    check = KubeVirtHandlerCheck("kubevirt_handler", {}, [instance])
    captured_part_map = {}
    check.set_metadata = lambda name, value, **options: captured_part_map.update(options.get("part_map", {}))
    sample = SimpleNamespace(labels={"kubeversion": "v4.5.6"})
    check.configure_metadata_transformer(None, [(sample,)], None)
    assert captured_part_map == {"major": "4", "minor": "5", "patch": "6"}


def test_transformer_skips_unmapped_metric_without_stopping_the_loop(instance):
    # Kills the core/ReplaceContinueWithBreak mutant at check.py:116 (continue -> break stops early).
    check = KubeVirtHandlerCheck("kubevirt_handler", {}, [instance])
    check._parse_config()
    check._init_base_tags()
    transform = check.configure_transformer_kubevirt_metrics()

    class RecordingSampleData:
        def __init__(self, samples):
            self.samples = samples
            self.consumed = 0

        def __iter__(self):
            for item in self.samples:
                self.consumed += 1
                yield item

    sample_data = RecordingSampleData([(SimpleNamespace(value=1), [], None), (SimpleNamespace(value=2), [], None)])
    metric = SimpleNamespace(name="not_a_kubevirt_metric", type="gauge")
    transform(metric, sample_data, None)
    assert sample_data.consumed == 2


def test_transform_extracts_name_from_dict_metric_mapping(instance, aggregator, monkeypatch):
    # Kills the core/AddNot mutant at check.py:123 (negating isinstance skips dict-name extraction).
    monkeypatch.setitem(check_module.METRICS_MAP, "custom_dict_metric", {"name": "custom.metric"})
    check = KubeVirtHandlerCheck("kubevirt_handler", {}, [instance])
    check._parse_config()
    check._init_base_tags()
    transform = check.configure_transformer_kubevirt_metrics()
    metric = SimpleNamespace(name="custom_dict_metric", type="gauge")
    sample = SimpleNamespace(value=42)
    transform(metric, [(sample, [], None)], None)
    aggregator.assert_metric("kubevirt_handler.custom.metric", 42)


def test_transform_leaves_plain_string_mapping_untouched_despite_name_substring(instance, aggregator, monkeypatch):
    # Kills the core/ReplaceAndWithOr mutant at check.py:123 ("name" substring check must not run alone).
    monkeypatch.setitem(check_module.METRICS_MAP, "custom_string_metric", "custom.rename")
    check = KubeVirtHandlerCheck("kubevirt_handler", {}, [instance])
    check._parse_config()
    check._init_base_tags()
    transform = check.configure_transformer_kubevirt_metrics()
    metric = SimpleNamespace(name="custom_string_metric", type="gauge")
    sample = SimpleNamespace(value=7)
    transform(metric, [(sample, [], None)], None)
    aggregator.assert_metric("kubevirt_handler.custom.rename", 7)


def test_counter_type_is_matched_by_value_not_identity(instance, aggregator):
    # Kills the core/ReplaceComparisonOperator_Eq_Is and _Eq_Lt mutants at check.py:127 for `metric_type ==
    # "counter"`: a value-equal-but-not-interned type must still route to self.count, without any scraper
    # configured to serve the (wrong) fallback branch.
    check = KubeVirtHandlerCheck("kubevirt_handler", {}, [instance])
    check._parse_config()
    check._init_base_tags()
    transform = check.configure_transformer_kubevirt_metrics()
    metric = SimpleNamespace(name="kubevirt_info", type=RUNTIME_COUNTER_TYPE)
    sample = SimpleNamespace(value=5)
    transform(metric, [(sample, [], None)], None)
    aggregator.assert_metric("kubevirt_handler.info.count", 5)


def test_gauge_type_is_matched_by_value_not_identity(instance, aggregator):
    # Kills the core/ReplaceComparisonOperator_Eq_Is and _Eq_Lt mutants at check.py:129 for `metric_type ==
    # "gauge"`: a value-equal-but-not-interned type must still route to self.gauge, without any scraper
    # configured to serve the (wrong) fallback branch.
    check = KubeVirtHandlerCheck("kubevirt_handler", {}, [instance])
    check._parse_config()
    check._init_base_tags()
    transform = check.configure_transformer_kubevirt_metrics()
    metric = SimpleNamespace(name="kubevirt_info", type=RUNTIME_GAUGE_TYPE)
    sample = SimpleNamespace(value=9)
    transform(metric, [(sample, [], None)], None)
    aggregator.assert_metric("kubevirt_handler.info", 9)


def test_unrecognized_type_falls_through_both_counter_and_gauge_branches(instance):
    # Kills the core/ReplaceComparisonOperator_Eq_LtE mutants at check.py:127 and check.py:129: an empty
    # metric_type is lexicographically <= both "counter" and "gauge", so a `<=` mutant would wrongly match
    # one of those branches instead of falling through to the native-transformer lookup, which raises
    # KeyError for an unrecognized OpenMetrics type.
    check = KubeVirtHandlerCheck("kubevirt_handler", {}, [instance])
    check._parse_config()
    check.configure_scrapers()
    check._init_base_tags()
    transform = check.configure_transformer_kubevirt_metrics()
    metric = SimpleNamespace(name="kubevirt_info", type="")
    sample = SimpleNamespace(value=1)
    with pytest.raises(KeyError):
        transform(metric, [(sample, [], None)], None)
