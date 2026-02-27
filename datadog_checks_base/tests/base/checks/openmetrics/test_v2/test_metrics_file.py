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
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def check():
    instance = {'openmetrics_endpoint': 'http://test:9090/metrics'}
    c = OpenMetricsBaseCheckV2('test', {}, [instance])
    c.__NAMESPACE__ = 'test'
    return c


@pytest.fixture
def make_check():
    def _factory(cls=None, instance=None):
        if cls is None:
            cls = OpenMetricsBaseCheckV2
        if instance is None:
            instance = {}
        instance.setdefault('openmetrics_endpoint', 'http://test:9090/metrics')
        c = cls('test', {}, [instance])
        c.__NAMESPACE__ = 'test'
        return c

    return _factory


# ---------------------------------------------------------------------------
# MetricsPredicate protocol
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "predicate_instance",
    [
        ConfigOptionTruthy("opt"),
        ConfigOptionEquals("opt", "v"),
        AllOf(ConfigOptionTruthy("a")),
        AnyOf(ConfigOptionTruthy("a")),
    ],
    ids=["ConfigOptionTruthy", "ConfigOptionEquals", "AllOf", "AnyOf"],
)
def test_predicate_satisfies_protocol(predicate_instance):
    assert isinstance(predicate_instance, MetricsPredicate)


def test_custom_class_satisfies_protocol():
    class Custom:
        def should_load(self, config):
            return True

    assert isinstance(Custom(), MetricsPredicate)


# ---------------------------------------------------------------------------
# ConfigOptionTruthy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "config, default, expected",
    [
        ({"go_metrics": True}, True, True),
        ({"go_metrics": False}, True, False),
        ({}, True, True),
        ({}, False, False),
        ({"opt": "yes"}, True, True),
        ({"opt": "no"}, True, False),
    ],
    ids=["present_true", "present_false", "missing_default_true", "missing_default_false", "string_yes", "string_no"],
)
def test_config_option_truthy(config, default, expected):
    option = next(iter(config)) if config else "go_metrics"
    pred = ConfigOptionTruthy(option, default=default)
    assert pred.should_load(config) is expected


# ---------------------------------------------------------------------------
# ConfigOptionEquals
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "config, option, value, expected",
    [
        ({"mode": "advanced"}, "mode", "advanced", True),
        ({"mode": "basic"}, "mode", "advanced", False),
        ({}, "mode", "advanced", False),
        ({}, "mode", None, True),
        ({"level": 3}, "level", 3, True),
    ],
    ids=["equal", "not_equal", "missing_key", "none_value", "integer_value"],
)
def test_config_option_equals(config, option, value, expected):
    pred = ConfigOptionEquals(option, value)
    assert pred.should_load(config) is expected


# ---------------------------------------------------------------------------
# AllOf / AnyOf
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "config, expected",
    [
        ({"a": True, "b": True}, True),
        ({"a": True, "b": False}, False),
        ({"a": False, "b": False}, False),
    ],
    ids=["all_true", "one_false", "all_false"],
)
def test_all_of(config, expected):
    pred = AllOf(ConfigOptionTruthy("a"), ConfigOptionTruthy("b"))
    assert pred.should_load(config) is expected


def test_all_of_mixed_predicate_types():
    pred = AllOf(ConfigOptionTruthy("enabled"), ConfigOptionEquals("mode", "full"))
    assert pred.should_load({"enabled": True, "mode": "full"}) is True
    assert pred.should_load({"enabled": True, "mode": "basic"}) is False


@pytest.mark.parametrize(
    "config, expected",
    [
        ({"a": True, "b": True}, True),
        ({"a": True, "b": False}, True),
        ({"a": False, "b": False}, False),
    ],
    ids=["all_true", "one_true", "all_false"],
)
def test_any_of(config, expected):
    pred = AnyOf(ConfigOptionTruthy("a"), ConfigOptionTruthy("b"))
    assert pred.should_load(config) is expected


def test_any_of_mixed_predicate_types():
    pred = AnyOf(ConfigOptionTruthy("extended", default=False), ConfigOptionEquals("profile", "full"))
    assert pred.should_load({"profile": "full"}) is True
    assert pred.should_load({"extended": True}) is True
    assert pred.should_load({}) is False


# ---------------------------------------------------------------------------
# MetricsFile dataclass
# ---------------------------------------------------------------------------


def test_metrics_file_is_frozen():
    mf = MetricsFile(Path("metrics.yaml"))
    with pytest.raises(AttributeError):
        mf.path = Path("other.yaml")


def test_metrics_file_no_predicate():
    mf = MetricsFile(Path("metrics.yaml"))
    assert mf.predicate is None


def test_metrics_file_with_predicate():
    pred = ConfigOptionTruthy("opt")
    mf = MetricsFile(Path("metrics.yaml"), predicate=pred)
    assert mf.predicate is pred


# ---------------------------------------------------------------------------
# _get_package_dir (basic check from OpenMetrics context)
# ---------------------------------------------------------------------------


def test_get_package_dir_returns_existing_directory(check):
    result = check._get_package_dir()
    assert isinstance(result, Path)
    assert result.is_dir()


# ---------------------------------------------------------------------------
# _load_metrics_file
# ---------------------------------------------------------------------------


def test_load_metrics_file_simple_mapping(check, tmp_path):
    data = {"go_goroutines": "go.goroutines", "go_threads": "go.threads"}
    (tmp_path / "go.yaml").write_text(yaml.dump(data))

    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        result = check._load_metrics_file(Path("go.yaml"))

    assert result == data


def test_load_metrics_file_full_config(check, tmp_path):
    data = {"http_requests_total": {"name": "http.requests", "type": "counter_gauge"}}
    (tmp_path / "full.yaml").write_text(yaml.dump(data))

    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        result = check._load_metrics_file(Path("full.yaml"))

    assert result == data


def test_load_metrics_file_missing_raises(check, tmp_path):
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        with pytest.raises(FileNotFoundError):
            check._load_metrics_file(Path("nonexistent.yaml"))


def test_load_metrics_file_malformed_yaml(check, tmp_path):
    (tmp_path / "broken.yaml").write_text("foo: [bar")
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        with pytest.raises(RuntimeError, match="Failed to parse metrics file"):
            check._load_metrics_file(Path("broken.yaml"))


def test_load_metrics_file_empty_file(check, tmp_path):
    (tmp_path / "empty.yaml").write_text("")
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        with pytest.raises(RuntimeError, match="must contain a YAML mapping, got NoneType"):
            check._load_metrics_file(Path("empty.yaml"))


def test_load_metrics_file_non_dict_content(check, tmp_path):
    (tmp_path / "list.yaml").write_text("[1, 2, 3]")
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        with pytest.raises(RuntimeError, match="must contain a YAML mapping, got list"):
            check._load_metrics_file(Path("list.yaml"))


# ---------------------------------------------------------------------------
# _load_file_based_metrics
# ---------------------------------------------------------------------------


def test_load_file_based_metrics_no_files_no_convention(check):
    result = check._load_file_based_metrics({})
    assert result == []


def test_load_file_based_metrics_convention_discovery(check, tmp_path):
    (tmp_path / "metrics.yml").write_text(yaml.dump({"raw_metric": "dd.metric"}))

    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        result = check._load_file_based_metrics({})

    assert len(result) == 1
    assert result[0] == {"raw_metric": "dd.metric"}


def test_load_file_based_metrics_explicit_files(make_check, tmp_path):
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir()
    (metrics_dir / "a.yaml").write_text(yaml.dump({"m1": "d1"}))
    (metrics_dir / "b.yaml").write_text(yaml.dump({"m2": "d2"}))

    class TestCheck(OpenMetricsBaseCheckV2):
        METRICS_FILES = [
            MetricsFile(Path("metrics/a.yaml")),
            MetricsFile(Path("metrics/b.yaml")),
        ]

    check = make_check(cls=TestCheck)
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        result = check._load_file_based_metrics({})

    assert len(result) == 2
    assert result[0] == {"m1": "d1"}
    assert result[1] == {"m2": "d2"}


def test_load_file_based_metrics_predicate_filters(make_check, tmp_path):
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir()
    (metrics_dir / "always.yaml").write_text(yaml.dump({"m1": "d1"}))
    (metrics_dir / "conditional.yaml").write_text(yaml.dump({"m2": "d2"}))

    class TestCheck(OpenMetricsBaseCheckV2):
        METRICS_FILES = [
            MetricsFile(Path("metrics/always.yaml")),
            MetricsFile(Path("metrics/conditional.yaml"), predicate=ConfigOptionTruthy("extra", default=False)),
        ]

    check = make_check(cls=TestCheck)

    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        result = check._load_file_based_metrics({})
    assert len(result) == 1
    assert result[0] == {"m1": "d1"}

    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        result = check._load_file_based_metrics({"extra": True})
    assert len(result) == 2


def test_load_file_based_metrics_explicit_skips_convention(make_check, tmp_path):
    (tmp_path / "metrics.yml").write_text(yaml.dump({"convention": "metric"}))
    (tmp_path / "explicit.yaml").write_text(yaml.dump({"explicit": "metric"}))

    class TestCheck(OpenMetricsBaseCheckV2):
        METRICS_FILES = [MetricsFile(Path("explicit.yaml"))]

    check = make_check(cls=TestCheck)
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        result = check._load_file_based_metrics({})

    assert len(result) == 1
    assert result[0] == {"explicit": "metric"}


# ---------------------------------------------------------------------------
# get_config_with_defaults integration
# ---------------------------------------------------------------------------


def test_get_config_with_defaults_merges_file_metrics(check, tmp_path):
    (tmp_path / "metrics.yml").write_text(yaml.dump({"raw": "dd_name"}))

    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        config = check.get_config_with_defaults({"openmetrics_endpoint": "http://test:9090/metrics"})

    assert {"raw": "dd_name"} in config["metrics"]


def test_get_config_with_defaults_combines_with_existing(make_check, tmp_path):
    (tmp_path / "metrics.yml").write_text(yaml.dump({"file_metric": "dd.file_metric"}))

    class TestCheck(OpenMetricsBaseCheckV2):
        def get_default_config(self):
            return {"metrics": [{"existing": "metric"}], "extra_option": True}

    check = make_check(cls=TestCheck)
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        config = check.get_config_with_defaults({"openmetrics_endpoint": "http://test:9090/metrics"})

    assert {"existing": "metric"} in config["metrics"]
    assert {"file_metric": "dd.file_metric"} in config["metrics"]
    assert config["extra_option"] is True


def test_get_config_with_defaults_no_files(make_check):
    class TestCheck(OpenMetricsBaseCheckV2):
        def get_default_config(self):
            return {"some_option": "value"}

    check = make_check(cls=TestCheck)
    config = check.get_config_with_defaults({"openmetrics_endpoint": "http://test:9090/metrics"})

    assert config.get("some_option") == "value"
    assert "metrics" not in config or config["metrics"] == []
