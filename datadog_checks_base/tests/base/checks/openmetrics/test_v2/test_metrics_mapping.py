# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.metrics_mapping import (
    AllOf,
    AnyOf,
    ConfigOptionEquals,
    ConfigOptionTruthy,
    MetricsMapping,
    MetricsPredicate,
)


@pytest.fixture
def make_check():
    def _factory(cls=None):
        cls = cls or OpenMetricsBaseCheckV2
        c = cls('test', {}, [{'openmetrics_endpoint': 'http://test:9090/metrics'}])
        c.__NAMESPACE__ = 'test'
        return c

    return _factory


def _write_yaml(tmp_path, filename, data):
    path = tmp_path / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data))
    return path


# ---------------------------------------------------------------------------
# MetricsPredicate protocol
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "instance",
    [
        ConfigOptionTruthy("x"),
        ConfigOptionEquals("x", 1),
        AllOf(ConfigOptionTruthy("x")),
        AnyOf(ConfigOptionTruthy("x")),
    ],
    ids=["truthy", "equals", "all_of", "any_of"],
)
def test_predicate_satisfies_protocol(instance):
    assert isinstance(instance, MetricsPredicate)


# ---------------------------------------------------------------------------
# ConfigOptionTruthy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "config, default, expected",
    [
        ({"opt": True}, True, True),
        ({"opt": False}, True, False),
        ({}, True, True),
        ({}, False, False),
        ({"opt": "yes"}, True, True),
        ({"opt": "no"}, True, False),
    ],
    ids=["true", "false", "missing_default_true", "missing_default_false", "string_yes", "string_no"],
)
def test_config_option_truthy(config, default, expected):
    pred = ConfigOptionTruthy("opt", default=default)
    assert pred.should_load(config) is expected


# ---------------------------------------------------------------------------
# ConfigOptionEquals
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "config, value, expected",
    [
        ({"mode": "advanced"}, "advanced", True),
        ({"mode": "basic"}, "advanced", False),
        ({}, "advanced", False),
        ({}, None, True),
    ],
    ids=["equal", "not_equal", "missing", "none_matches_missing"],
)
def test_config_option_equals(config, value, expected):
    pred = ConfigOptionEquals("mode", value)
    assert pred.should_load(config) is expected


# ---------------------------------------------------------------------------
# AllOf / AnyOf
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cls, config, expected",
    [
        (AllOf, {"a": True, "b": True}, True),
        (AllOf, {"a": True, "b": False}, False),
        (AllOf, {"a": False, "b": False}, False),
        (AnyOf, {"a": True, "b": True}, True),
        (AnyOf, {"a": True, "b": False}, True),
        (AnyOf, {"a": False, "b": False}, False),
    ],
    ids=["all_both", "all_one", "all_none", "any_both", "any_one", "any_none"],
)
def test_composite_predicates(cls, config, expected):
    pred = cls(ConfigOptionTruthy("a"), ConfigOptionTruthy("b"))
    assert pred.should_load(config) is expected


# ---------------------------------------------------------------------------
# MetricsMapping
# ---------------------------------------------------------------------------


def test_metrics_mapping_is_frozen():
    mm = MetricsMapping(Path("m.yaml"))
    with pytest.raises(AttributeError):
        mm.path = Path("other.yaml")


def test_metrics_mapping_should_load_no_predicate():
    mm = MetricsMapping(Path("m.yaml"))
    assert mm.should_load({}) is True


def test_metrics_mapping_should_load_with_predicate():
    mm = MetricsMapping(Path("m.yaml"), predicate=ConfigOptionTruthy("opt", default=False))
    assert mm.should_load({}) is False
    assert mm.should_load({"opt": True}) is True


# ---------------------------------------------------------------------------
# _load_metrics_file
# ---------------------------------------------------------------------------


def test_load_metrics_file(make_check, tmp_path):
    _write_yaml(tmp_path, "go.yaml", {"go_goroutines": "go.goroutines"})
    check = make_check()
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        assert check._load_metrics_file(Path("go.yaml")) == {"go_goroutines": "go.goroutines"}


@pytest.mark.parametrize(
    "filename, content, match",
    [
        ("broken.yaml", "foo: [bar", "Failed to parse"),
        ("empty.yaml", "", "must contain a YAML mapping, got NoneType"),
        ("list.yaml", "[1, 2, 3]", "must contain a YAML mapping, got list"),
    ],
    ids=["malformed", "empty", "non_dict"],
)
def test_load_metrics_file_errors(make_check, tmp_path, filename, content, match):
    (tmp_path / filename).write_text(content)
    check = make_check()
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        with pytest.raises(RuntimeError, match=match):
            check._load_metrics_file(Path(filename))


def test_load_metrics_file_missing(make_check, tmp_path):
    check = make_check()
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        with pytest.raises(FileNotFoundError):
            check._load_metrics_file(Path("nonexistent.yaml"))


# ---------------------------------------------------------------------------
# _load_file_based_metrics
# ---------------------------------------------------------------------------


def test_load_file_based_metrics_no_files(make_check):
    assert make_check()._load_file_based_metrics({}) == []


def test_load_file_based_metrics_convention_discovery(make_check, tmp_path):
    _write_yaml(tmp_path, "metrics.yml", {"raw": "dd.raw"})
    check = make_check()
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        result = check._load_file_based_metrics({})
    assert result == [{"raw": "dd.raw"}]


def test_load_file_based_metrics_explicit(make_check, tmp_path):
    _write_yaml(tmp_path, "metrics/a.yaml", {"m1": "d1"})
    _write_yaml(tmp_path, "metrics/b.yaml", {"m2": "d2"})

    class Check(OpenMetricsBaseCheckV2):
        METRICS_MAP = [MetricsMapping(Path("metrics/a.yaml")), MetricsMapping(Path("metrics/b.yaml"))]

    check = make_check(cls=Check)
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        result = check._load_file_based_metrics({})
    assert result == [{"m1": "d1"}, {"m2": "d2"}]


def test_load_file_based_metrics_predicate_filters(make_check, tmp_path):
    _write_yaml(tmp_path, "metrics/always.yaml", {"m1": "d1"})
    _write_yaml(tmp_path, "metrics/conditional.yaml", {"m2": "d2"})

    class Check(OpenMetricsBaseCheckV2):
        METRICS_MAP = [
            MetricsMapping(Path("metrics/always.yaml")),
            MetricsMapping(Path("metrics/conditional.yaml"), predicate=ConfigOptionTruthy("extra", default=False)),
        ]

    check = make_check(cls=Check)
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        assert len(check._load_file_based_metrics({})) == 1
        assert len(check._load_file_based_metrics({"extra": True})) == 2


def test_load_file_based_metrics_explicit_skips_convention(make_check, tmp_path):
    _write_yaml(tmp_path, "metrics.yml", {"convention": "metric"})
    _write_yaml(tmp_path, "explicit.yaml", {"explicit": "metric"})

    class Check(OpenMetricsBaseCheckV2):
        METRICS_MAP = [MetricsMapping(Path("explicit.yaml"))]

    check = make_check(cls=Check)
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        result = check._load_file_based_metrics({})
    assert result == [{"explicit": "metric"}]


# ---------------------------------------------------------------------------
# get_config_with_defaults
# ---------------------------------------------------------------------------


def test_get_config_with_defaults_merges_file_metrics(make_check, tmp_path):
    _write_yaml(tmp_path, "metrics.yml", {"raw": "dd_name"})
    check = make_check()
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        config = check.get_config_with_defaults({"openmetrics_endpoint": "http://test:9090/metrics"})
    assert {"raw": "dd_name"} in config["metrics"]


def test_get_config_with_defaults_combines_with_existing(make_check, tmp_path):
    _write_yaml(tmp_path, "metrics.yml", {"file_metric": "dd.file_metric"})

    class Check(OpenMetricsBaseCheckV2):
        def get_default_config(self):
            return {"metrics": [{"existing": "metric"}], "extra_option": True}

    check = make_check(cls=Check)
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        config = check.get_config_with_defaults({"openmetrics_endpoint": "http://test:9090/metrics"})
    assert {"existing": "metric"} in config["metrics"]
    assert {"file_metric": "dd.file_metric"} in config["metrics"]
    assert config["extra_option"] is True
