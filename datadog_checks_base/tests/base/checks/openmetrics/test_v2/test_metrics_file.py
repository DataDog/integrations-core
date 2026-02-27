# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.metrics_file import (
    AllOf,
    AnyOf,
    ConfigOptionEquals,
    ConfigOptionTruthy,
    MetricsFile,
    MetricsPredicate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_check(cls=None, instance=None):
    if cls is None:
        cls = OpenMetricsBaseCheckV2
    if instance is None:
        instance = {}
    instance.setdefault('openmetrics_endpoint', 'http://test:9090/metrics')
    check = cls('test', {}, [instance])
    check.__NAMESPACE__ = 'test'
    return check


# ---------------------------------------------------------------------------
# MetricsPredicate protocol
# ---------------------------------------------------------------------------


class TestMetricsPredicate:
    def test_config_option_truthy_is_predicate(self):
        assert isinstance(ConfigOptionTruthy("opt"), MetricsPredicate)

    def test_config_option_equals_is_predicate(self):
        assert isinstance(ConfigOptionEquals("opt", "v"), MetricsPredicate)

    def test_all_of_is_predicate(self):
        assert isinstance(AllOf(ConfigOptionTruthy("a")), MetricsPredicate)

    def test_any_of_is_predicate(self):
        assert isinstance(AnyOf(ConfigOptionTruthy("a")), MetricsPredicate)

    def test_custom_class_satisfies_protocol(self):
        class Custom:
            def should_load(self, config):
                return True

        assert isinstance(Custom(), MetricsPredicate)


# ---------------------------------------------------------------------------
# ConfigOptionTruthy
# ---------------------------------------------------------------------------


class TestConfigOptionTruthy:
    def test_option_present_true(self):
        pred = ConfigOptionTruthy("go_metrics")
        assert pred.should_load({"go_metrics": True}) is True

    def test_option_present_false(self):
        pred = ConfigOptionTruthy("go_metrics")
        assert pred.should_load({"go_metrics": False}) is False

    def test_option_missing_default_true(self):
        pred = ConfigOptionTruthy("go_metrics")
        assert pred.should_load({}) is True

    def test_option_missing_default_false(self):
        pred = ConfigOptionTruthy("go_metrics", default=False)
        assert pred.should_load({}) is False

    def test_string_yes(self):
        pred = ConfigOptionTruthy("opt")
        assert pred.should_load({"opt": "yes"}) is True

    def test_string_no(self):
        pred = ConfigOptionTruthy("opt")
        assert pred.should_load({"opt": "no"}) is False


# ---------------------------------------------------------------------------
# ConfigOptionEquals
# ---------------------------------------------------------------------------


class TestConfigOptionEquals:
    def test_equal(self):
        pred = ConfigOptionEquals("mode", "advanced")
        assert pred.should_load({"mode": "advanced"}) is True

    def test_not_equal(self):
        pred = ConfigOptionEquals("mode", "advanced")
        assert pred.should_load({"mode": "basic"}) is False

    def test_missing_key(self):
        pred = ConfigOptionEquals("mode", "advanced")
        assert pred.should_load({}) is False

    def test_none_value(self):
        pred = ConfigOptionEquals("mode", None)
        assert pred.should_load({}) is True

    def test_integer_value(self):
        pred = ConfigOptionEquals("level", 3)
        assert pred.should_load({"level": 3}) is True


# ---------------------------------------------------------------------------
# AllOf
# ---------------------------------------------------------------------------


class TestAllOf:
    def test_all_true(self):
        pred = AllOf(ConfigOptionTruthy("a"), ConfigOptionTruthy("b"))
        assert pred.should_load({"a": True, "b": True}) is True

    def test_one_false(self):
        pred = AllOf(ConfigOptionTruthy("a"), ConfigOptionTruthy("b"))
        assert pred.should_load({"a": True, "b": False}) is False

    def test_all_false(self):
        pred = AllOf(ConfigOptionTruthy("a"), ConfigOptionTruthy("b"))
        assert pred.should_load({"a": False, "b": False}) is False

    def test_mixed_predicate_types(self):
        pred = AllOf(
            ConfigOptionTruthy("enabled"),
            ConfigOptionEquals("mode", "full"),
        )
        assert pred.should_load({"enabled": True, "mode": "full"}) is True
        assert pred.should_load({"enabled": True, "mode": "basic"}) is False


# ---------------------------------------------------------------------------
# AnyOf
# ---------------------------------------------------------------------------


class TestAnyOf:
    def test_all_true(self):
        pred = AnyOf(ConfigOptionTruthy("a"), ConfigOptionTruthy("b"))
        assert pred.should_load({"a": True, "b": True}) is True

    def test_one_true(self):
        pred = AnyOf(ConfigOptionTruthy("a"), ConfigOptionTruthy("b"))
        assert pred.should_load({"a": True, "b": False}) is True

    def test_all_false(self):
        pred = AnyOf(ConfigOptionTruthy("a"), ConfigOptionTruthy("b"))
        assert pred.should_load({"a": False, "b": False}) is False

    def test_mixed_predicate_types(self):
        pred = AnyOf(
            ConfigOptionTruthy("extended", default=False),
            ConfigOptionEquals("profile", "full"),
        )
        assert pred.should_load({"profile": "full"}) is True
        assert pred.should_load({"extended": True}) is True
        assert pred.should_load({}) is False


# ---------------------------------------------------------------------------
# MetricsFile dataclass
# ---------------------------------------------------------------------------


class TestMetricsFile:
    def test_frozen(self):
        mf = MetricsFile(Path("metrics.yaml"))
        with pytest.raises(AttributeError):
            mf.path = Path("other.yaml")

    def test_no_predicate(self):
        mf = MetricsFile(Path("metrics.yaml"))
        assert mf.predicate is None

    def test_with_predicate(self):
        pred = ConfigOptionTruthy("opt")
        mf = MetricsFile(Path("metrics.yaml"), predicate=pred)
        assert mf.predicate is pred


# ---------------------------------------------------------------------------
# _get_package_dir
# ---------------------------------------------------------------------------


class TestGetPackageDir:
    def test_returns_path(self):
        check = _make_check()
        result = check._get_package_dir()
        assert isinstance(result, Path)
        assert result.is_dir()


# ---------------------------------------------------------------------------
# File-based metrics loading on OpenMetricsBaseCheckV2
# ---------------------------------------------------------------------------


class TestLoadFileBasedMetrics:
    def test_no_metrics_files_no_convention_file(self):
        check = _make_check()
        result = check._load_file_based_metrics({})
        assert result == []

    def test_convention_based_discovery(self, tmp_path):
        metrics_yml = tmp_path / "metrics.yml"
        metrics_data = {"raw_metric": "dd.metric"}
        metrics_yml.write_text(yaml.dump(metrics_data))

        check = _make_check()
        with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
            result = check._load_file_based_metrics({})

        assert len(result) == 1
        assert result[0] == {"raw_metric": "dd.metric"}

    def test_explicit_metrics_files(self, tmp_path):
        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()
        (metrics_dir / "a.yaml").write_text(yaml.dump({"m1": "d1"}))
        (metrics_dir / "b.yaml").write_text(yaml.dump({"m2": "d2"}))

        class TestCheck(OpenMetricsBaseCheckV2):
            METRICS_FILES = [
                MetricsFile(Path("metrics/a.yaml")),
                MetricsFile(Path("metrics/b.yaml")),
            ]

        check = _make_check(cls=TestCheck)
        with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
            result = check._load_file_based_metrics({})

        assert len(result) == 2
        assert result[0] == {"m1": "d1"}
        assert result[1] == {"m2": "d2"}

    def test_predicate_filters_files(self, tmp_path):
        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()
        (metrics_dir / "always.yaml").write_text(yaml.dump({"m1": "d1"}))
        (metrics_dir / "conditional.yaml").write_text(yaml.dump({"m2": "d2"}))

        class TestCheck(OpenMetricsBaseCheckV2):
            METRICS_FILES = [
                MetricsFile(Path("metrics/always.yaml")),
                MetricsFile(Path("metrics/conditional.yaml"), predicate=ConfigOptionTruthy("extra", default=False)),
            ]

        check = _make_check(cls=TestCheck)

        # Without the option: only the unconditional file is loaded
        with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
            result = check._load_file_based_metrics({})
        assert len(result) == 1
        assert result[0] == {"m1": "d1"}

        # With the option: both files are loaded
        with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
            result = check._load_file_based_metrics({"extra": True})
        assert len(result) == 2

    def test_explicit_files_skip_convention_discovery(self, tmp_path):
        """When METRICS_FILES is set, metrics.yml should not be auto-discovered."""
        (tmp_path / "metrics.yml").write_text(yaml.dump({"convention": "metric"}))
        (tmp_path / "explicit.yaml").write_text(yaml.dump({"explicit": "metric"}))

        class TestCheck(OpenMetricsBaseCheckV2):
            METRICS_FILES = [
                MetricsFile(Path("explicit.yaml")),
            ]

        check = _make_check(cls=TestCheck)
        with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
            result = check._load_file_based_metrics({})

        assert len(result) == 1
        assert result[0] == {"explicit": "metric"}


class TestGetConfigWithDefaults:
    def test_file_metrics_merged_into_defaults(self, tmp_path):
        metrics_yml = tmp_path / "metrics.yml"
        metrics_yml.write_text(yaml.dump({"raw": "dd_name"}))

        check = _make_check()
        with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
            config = check.get_config_with_defaults({"openmetrics_endpoint": "http://test:9090/metrics"})

        assert {"raw": "dd_name"} in config["metrics"]

    def test_file_metrics_combined_with_default_config(self, tmp_path):
        metrics_yml = tmp_path / "metrics.yml"
        metrics_yml.write_text(yaml.dump({"file_metric": "dd.file_metric"}))

        class TestCheck(OpenMetricsBaseCheckV2):
            def get_default_config(self):
                return {"metrics": [{"existing": "metric"}], "extra_option": True}

        check = _make_check(cls=TestCheck)
        with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
            config = check.get_config_with_defaults({"openmetrics_endpoint": "http://test:9090/metrics"})

        assert {"existing": "metric"} in config["metrics"]
        assert {"file_metric": "dd.file_metric"} in config["metrics"]
        assert config["extra_option"] is True

    def test_no_files_returns_only_defaults(self):
        class TestCheck(OpenMetricsBaseCheckV2):
            def get_default_config(self):
                return {"some_option": "value"}

        check = _make_check(cls=TestCheck)
        config = check.get_config_with_defaults({"openmetrics_endpoint": "http://test:9090/metrics"})

        assert config.get("some_option") == "value"
        assert "metrics" not in config or config["metrics"] == []


class TestLoadMetricsFile:
    def test_loads_simple_mapping(self, tmp_path):
        data = {"go_goroutines": "go.goroutines", "go_threads": "go.threads"}
        (tmp_path / "go.yaml").write_text(yaml.dump(data))

        check = _make_check()
        with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
            result = check._load_metrics_file(Path("go.yaml"))

        assert result == data

    def test_loads_full_config(self, tmp_path):
        data = {"http_requests_total": {"name": "http.requests", "type": "counter_gauge"}}
        (tmp_path / "full.yaml").write_text(yaml.dump(data))

        check = _make_check()
        with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
            result = check._load_metrics_file(Path("full.yaml"))

        assert result == data

    def test_missing_file_raises(self, tmp_path):
        check = _make_check()
        with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
            with pytest.raises(FileNotFoundError):
                check._load_metrics_file(Path("nonexistent.yaml"))
