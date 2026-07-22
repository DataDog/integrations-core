# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path
from typing import Protocol
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
)
from datadog_checks.base.errors import ConfigurationError

_DEFAULT_INSTANCE: dict[str, object] = {'openmetrics_endpoint': 'http://test:9090/metrics'}


class CheckFactory(Protocol):
    def __call__(
        self,
        cls: type[OpenMetricsBaseCheckV2] | None = None,
        instance: dict[str, object] | None = None,
    ) -> OpenMetricsBaseCheckV2: ...


@pytest.fixture
def make_check() -> CheckFactory:
    def factory(cls=None, instance=None):
        cls = cls or OpenMetricsBaseCheckV2
        inst = _DEFAULT_INSTANCE | (instance or {})
        c = cls('test', {}, [inst])
        c.__NAMESPACE__ = 'test'
        return c

    return factory


def write_yaml(tmp_path, filename, data):
    path = tmp_path / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data))
    return path


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
def test_config_option_truthy(config: dict[str, object], default: bool, expected: bool):
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
def test_config_option_equals(config: dict[str, str], value: str | None, expected: bool):
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
def test_composite_predicates(cls: type[AllOf] | type[AnyOf], config: dict[str, bool], expected: bool):
    pred = cls(ConfigOptionTruthy("a"), ConfigOptionTruthy("b"))
    assert pred.should_load(config) is expected


@pytest.mark.parametrize(
    "cls, expected",
    [
        (AllOf, True),
        (AnyOf, False),
    ],
    ids=["all_of_vacuous_truth", "any_of_vacuous_falsity"],
)
def test_composite_predicates_empty(cls: type[AllOf] | type[AnyOf], expected: bool):
    assert cls().should_load({}) is expected


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


def test_load_metrics_file(make_check: CheckFactory, tmp_path: Path):
    write_yaml(tmp_path, "go.yaml", {"go_goroutines": "go.goroutines"})
    check = make_check()
    assert check._load_metrics_file(tmp_path / "go.yaml") == {"go_goroutines": "go.goroutines"}


@pytest.mark.parametrize(
    "filename, content, match",
    [
        ("broken.yaml", "foo: [bar", "Failed to parse"),
        ("empty.yaml", "", "must contain a YAML mapping, got NoneType"),
        ("list.yaml", "[1, 2, 3]", "must contain a YAML mapping, got list"),
    ],
    ids=["malformed", "empty", "non_dict"],
)
def test_load_metrics_file_errors(make_check: CheckFactory, tmp_path: Path, filename: str, content: str, match: str):
    (tmp_path / filename).write_text(content)
    check = make_check()
    with pytest.raises(ConfigurationError, match=match):
        check._load_metrics_file(tmp_path / filename)


def test_load_metrics_file_missing(make_check: CheckFactory, tmp_path: Path):
    check = make_check()
    with pytest.raises(ConfigurationError, match="Failed to read metrics file"):
        check._load_metrics_file(tmp_path / "nonexistent.yaml")


# ---------------------------------------------------------------------------
# _load_file_based_metrics
# ---------------------------------------------------------------------------


def test_load_file_based_metrics_no_files(make_check: CheckFactory, tmp_path: Path):
    check = make_check()
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        assert check._load_file_based_metrics({}) == []


@pytest.mark.parametrize("filename", ["metrics.yaml", "metrics.yml"])
def test_load_file_based_metrics_convention_discovery(make_check: CheckFactory, tmp_path: Path, filename: str):
    write_yaml(tmp_path, filename, {"raw": "dd.raw"})
    check = make_check()
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        result = check._load_file_based_metrics({})
    assert result == [{"raw": "dd.raw"}]


def test_load_file_based_metrics_convention_yaml_takes_precedence(make_check: CheckFactory, tmp_path: Path):
    write_yaml(tmp_path, "metrics.yaml", {"from_yaml": "dd.yaml"})
    write_yaml(tmp_path, "metrics.yml", {"from_yml": "dd.yml"})
    check = make_check()
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        result = check._load_file_based_metrics({})
    assert result == [{"from_yaml": "dd.yaml"}]


def test_load_file_based_metrics_explicit(make_check: CheckFactory, tmp_path: Path):
    write_yaml(tmp_path, "metrics/a.yaml", {"m1": "d1"})
    write_yaml(tmp_path, "metrics/b.yaml", {"m2": "d2"})

    class Check(OpenMetricsBaseCheckV2):
        METRICS_MAP = (MetricsMapping(Path("metrics/a.yaml")), MetricsMapping(Path("metrics/b.yaml")))

    check = make_check(cls=Check)
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        result = check._load_file_based_metrics({})
    assert result == [{"m1": "d1"}, {"m2": "d2"}]


def test_load_file_based_metrics_predicate_filters(make_check: CheckFactory, tmp_path: Path):
    write_yaml(tmp_path, "metrics/always.yaml", {"m1": "d1"})
    write_yaml(tmp_path, "metrics/conditional.yaml", {"m2": "d2"})

    class Check(OpenMetricsBaseCheckV2):
        METRICS_MAP = (
            MetricsMapping(Path("metrics/always.yaml")),
            MetricsMapping(Path("metrics/conditional.yaml"), predicate=ConfigOptionTruthy("extra", default=False)),
        )

    check_base = make_check(cls=Check)
    check_extra = make_check(cls=Check, instance={'extra': True})
    with patch.object(Check, '_get_package_dir', return_value=tmp_path):
        assert len(check_base._load_file_based_metrics(check_base.instance)) == 1
        assert len(check_extra._load_file_based_metrics(check_extra.instance)) == 2


def test_load_file_based_metrics_explicit_skips_convention(make_check: CheckFactory, tmp_path: Path):
    write_yaml(tmp_path, "metrics.yml", {"convention": "metric"})
    write_yaml(tmp_path, "explicit.yaml", {"explicit": "metric"})

    class Check(OpenMetricsBaseCheckV2):
        METRICS_MAP = (MetricsMapping(Path("explicit.yaml")),)

    check = make_check(cls=Check)
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        result = check._load_file_based_metrics({})
    assert result == [{"explicit": "metric"}]


# ---------------------------------------------------------------------------
# _load_file_based_metrics caching
# ---------------------------------------------------------------------------


def test_load_file_based_metrics_cached_across_calls(make_check: CheckFactory, tmp_path: Path):
    write_yaml(tmp_path, "metrics.yml", {"raw": "dd.raw"})
    check = make_check()
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        first = check._load_file_based_metrics({})
        second = check._load_file_based_metrics({})
    assert first is second


def test_load_file_based_metrics_cache_ignores_config_changes(make_check: CheckFactory, tmp_path: Path):
    """Predicate re-evaluation is suppressed once the cache is populated: a second call with a
    different config returns the first-call result without consulting the predicates again."""
    write_yaml(tmp_path, "metrics/always.yaml", {"m1": "d1"})
    write_yaml(tmp_path, "metrics/extra.yaml", {"m2": "d2"})

    class Check(OpenMetricsBaseCheckV2):
        METRICS_MAP = (
            MetricsMapping(Path("metrics/always.yaml")),
            MetricsMapping(Path("metrics/extra.yaml"), predicate=ConfigOptionTruthy("extra", default=False)),
        )

    check = make_check(cls=Check)
    with patch.object(Check, '_get_package_dir', return_value=tmp_path):
        first = check._load_file_based_metrics({'extra': False})
        second = check._load_file_based_metrics({'extra': True})
    assert first is second
    assert len(first) == 1


def test_load_file_based_metrics_permanent_failure_fails_once(make_check: CheckFactory, tmp_path: Path):
    """A malformed YAML file raises on the first call; subsequent calls return the empty cache."""
    (tmp_path / "metrics.yml").write_text("foo: [bar")
    check = make_check()
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        with pytest.raises(ConfigurationError, match="Failed to parse"):
            check._load_file_based_metrics({})
        assert check._load_file_based_metrics({}) == []


def test_load_file_based_metrics_multi_file_failure_seals_empty(make_check: CheckFactory, tmp_path: Path):
    """A mid-comprehension load failure discards earlier successes; the cache lands as []."""
    write_yaml(tmp_path, "metrics/a.yaml", {"a": "dd.a"})
    (tmp_path / "metrics" / "b.yaml").write_text("foo: [bar")
    write_yaml(tmp_path, "metrics/c.yaml", {"c": "dd.c"})

    class Check(OpenMetricsBaseCheckV2):
        METRICS_MAP = (
            MetricsMapping(Path("metrics/a.yaml")),
            MetricsMapping(Path("metrics/b.yaml")),
            MetricsMapping(Path("metrics/c.yaml")),
        )

    check = make_check(cls=Check)
    with patch.object(Check, '_get_package_dir', return_value=tmp_path):
        with pytest.raises(ConfigurationError, match="Failed to parse"):
            check._load_file_based_metrics({})
        assert check._load_file_based_metrics({}) == []


def test_load_file_based_metrics_does_not_accumulate_on_repeated_scraper_creation(
    make_check: CheckFactory, tmp_path: Path
):
    """Repeated create_scraper calls (e.g. from refresh_scrapers) must not grow the metrics list."""
    write_yaml(tmp_path, "metrics.yml", {"raw": "dd.raw"})
    check = make_check()
    instance = {'openmetrics_endpoint': 'http://test:9090/metrics'}
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        config_first = check.get_config_with_defaults(instance)
        config_second = check.get_config_with_defaults(instance)
    assert config_first['metrics'] == config_second['metrics']


def test_load_file_based_metrics_does_not_mutate_get_default_config(make_check: CheckFactory, tmp_path: Path):
    """File metrics must not mutate the list returned by get_default_config."""
    write_yaml(tmp_path, "metrics.yml", {"raw": "dd.raw"})
    SHARED_METRICS = [{"existing": "metric"}]

    class Check(OpenMetricsBaseCheckV2):
        def get_default_config(self):
            return {"metrics": SHARED_METRICS}

    check = make_check(cls=Check)
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        check.get_config_with_defaults({'openmetrics_endpoint': 'http://test:9090/metrics'})
    assert SHARED_METRICS == [{"existing": "metric"}]


def test_load_file_based_metrics_does_not_mutate_cached_default_dict(make_check: CheckFactory, tmp_path: Path):
    """A subclass that caches its defaults dict at module level must not see file metrics accumulate."""
    write_yaml(tmp_path, "metrics.yml", {"raw": "dd.raw"})
    CACHED_DEFAULTS = {"metrics": [{"existing": "metric"}]}

    class Check(OpenMetricsBaseCheckV2):
        def get_default_config(self):
            return CACHED_DEFAULTS

    instance = {'openmetrics_endpoint': 'http://test:9090/metrics'}
    first = make_check(cls=Check)
    second = make_check(cls=Check)
    with patch.object(Check, '_get_package_dir', return_value=tmp_path):
        config_first = first.get_config_with_defaults(instance)
        config_second = second.get_config_with_defaults(instance)
    assert CACHED_DEFAULTS == {"metrics": [{"existing": "metric"}]}
    assert config_first['metrics'] == config_second['metrics']
    assert len(config_first['metrics']) == 2


# ---------------------------------------------------------------------------
# get_config_with_defaults
# ---------------------------------------------------------------------------


def test_get_config_with_defaults_merges_file_metrics(make_check: CheckFactory, tmp_path: Path):
    write_yaml(tmp_path, "metrics.yml", {"raw": "dd_name"})
    check = make_check()
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        config = check.get_config_with_defaults({"openmetrics_endpoint": "http://test:9090/metrics"})
    assert {"raw": "dd_name"} in config["metrics"]


def test_get_config_with_defaults_combines_with_existing(make_check: CheckFactory, tmp_path: Path):
    write_yaml(tmp_path, "metrics.yml", {"file_metric": "dd.file_metric"})

    class Check(OpenMetricsBaseCheckV2):
        def get_default_config(self):
            return {"metrics": [{"existing": "metric"}], "extra_option": True}

    check = make_check(cls=Check)
    with patch.object(type(check), '_get_package_dir', return_value=tmp_path):
        config = check.get_config_with_defaults({"openmetrics_endpoint": "http://test:9090/metrics"})
    assert {"existing": "metric"} in config["metrics"]
    assert {"file_metric": "dd.file_metric"} in config["metrics"]
    assert config["extra_option"] is True


# ---------------------------------------------------------------------------
# Public re-exports (lazy_loader stub)
# ---------------------------------------------------------------------------


def test_public_reexports_resolve():
    """The lazy_loader stub at v2/__init__.pyi must expose the documented public surface."""
    from datadog_checks.base.checks.openmetrics.v2 import (
        AllOf,
        AnyOf,
        ConfigOptionEquals,
        ConfigOptionTruthy,
        MetricsMapping,
        MetricsPredicate,
        OpenMetricsBaseCheckV2,
    )

    assert all(
        symbol is not None
        for symbol in (
            AllOf,
            AnyOf,
            ConfigOptionEquals,
            ConfigOptionTruthy,
            MetricsMapping,
            MetricsPredicate,
            OpenMetricsBaseCheckV2,
        )
    )
