# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, runtime_checkable

from datadog_checks.base.config import is_affirmative

MetricsConfig = dict[str, str | dict[str, str]]
"""Type alias for the metric configuration loaded from a YAML file.

Each key is a raw Prometheus metric name, and the value is either:
- A string representing the Datadog metric name (simple renaming)
- A dict with ``name``, ``type``, and other fields (full config override)

Example::

    # Simple renaming
    {"go_goroutines": "go.goroutines"}

    # Full config with type override
    {"http_requests_total": {"name": "http.requests", "type": "counter_gauge"}}
"""


@runtime_checkable
class MetricsPredicate(Protocol):
    """Protocol for predicates that control whether a metrics file should be loaded.

    Implement this protocol to create custom loading conditions for metrics files.
    The ``should_load`` method receives the instance configuration and returns
    ``True`` if the associated metrics file should be loaded.

    Example::

        class MyCustomPredicate:
            def should_load(self, config: Mapping) -> bool:
                return config.get("my_option") == "enabled"

        METRICS_FILES = [
            MetricsFile(Path("metrics/custom.yaml"), predicate=MyCustomPredicate()),
        ]
    """

    def should_load(self, config: Mapping) -> bool: ...


class ConfigOptionTruthy:
    """Load a metrics file only if a configuration option is truthy.

    Uses ``is_affirmative`` to evaluate the config value, which accepts
    booleans, strings like ``"yes"``/``"true"``/``"1"``, and other types
    via their ``__bool__`` implementation.

    Args:
        option: The configuration option name to check.
        default: The default value if the option is not present in the config.
            Defaults to ``True`` (include metrics unless explicitly disabled).

    Example::

        METRICS_FILES = [
            MetricsFile(Path("metrics/go.yaml"), predicate=ConfigOptionTruthy("go_metrics")),
            MetricsFile(Path("metrics/debug.yaml"), predicate=ConfigOptionTruthy("debug_metrics", default=False)),
        ]
    """

    def __init__(self, option: str, default: bool = True) -> None:
        self.option = option
        self.default = default

    def should_load(self, config: Mapping) -> bool:
        return is_affirmative(config.get(self.option, self.default))


class ConfigOptionEquals:
    """Load a metrics file only if a configuration option equals a specific value.

    Performs an exact equality check between the config value and the expected value.

    Args:
        option: The configuration option name to check.
        value: The expected value to compare against.

    Example::

        METRICS_FILES = [
            MetricsFile(Path("metrics/advanced.yaml"), predicate=ConfigOptionEquals("mode", "advanced")),
        ]
    """

    def __init__(self, option: str, value: Any) -> None:
        self.option = option
        self.value = value

    def should_load(self, config: Mapping) -> bool:
        return config.get(self.option) == self.value


class AllOf:
    """Compose predicates so that all must pass for the metrics file to be loaded.

    Args:
        *predicates: Two or more predicates that must all return ``True``.

    Example::

        METRICS_FILES = [
            MetricsFile(
                Path("metrics/extra.yaml"),
                predicate=AllOf(
                    ConfigOptionTruthy("extra_metrics"),
                    ConfigOptionTruthy("verbose_mode"),
                ),
            ),
        ]
    """

    def __init__(self, *predicates: MetricsPredicate) -> None:
        self.predicates = predicates

    def should_load(self, config: Mapping) -> bool:
        return all(p.should_load(config) for p in self.predicates)


class AnyOf:
    """Compose predicates so that any one passing is sufficient to load the metrics file.

    Args:
        *predicates: Two or more predicates where at least one must return ``True``.

    Example::

        METRICS_FILES = [
            MetricsFile(
                Path("metrics/extended.yaml"),
                predicate=AnyOf(
                    ConfigOptionTruthy("extended_metrics"),
                    ConfigOptionEquals("profile", "full"),
                ),
            ),
        ]
    """

    def __init__(self, *predicates: MetricsPredicate) -> None:
        self.predicates = predicates

    def should_load(self, config: Mapping) -> bool:
        return any(p.should_load(config) for p in self.predicates)


@dataclass(frozen=True)
class MetricsFile:
    """Declares a YAML file containing metric name mappings to be loaded automatically.

    Use this in the ``METRICS_FILES`` class variable of an ``OpenMetricsBaseCheckV2``
    subclass to specify which YAML files provide metric mappings and under what
    conditions they should be loaded.

    The YAML file should contain a flat mapping of Prometheus metric names to
    Datadog metric names (or full config dicts).

    Args:
        path: Path to the YAML file, relative to the check's package directory.
            For example, ``Path("metrics/go.yaml")`` resolves to
            ``datadog_checks/<integration>/metrics/go.yaml``.
        predicate: An optional predicate that controls whether this file is loaded.
            If ``None``, the file is always loaded.

    Example::

        from pathlib import Path
        from datadog_checks.base.checks.openmetrics.v2.metrics_file import (
            ConfigOptionTruthy,
            MetricsFile,
        )

        class MyCheck(OpenMetricsBaseCheckV2):
            METRICS_FILES = [
                MetricsFile(Path("metrics/default.yaml")),
                MetricsFile(Path("metrics/go.yaml"), predicate=ConfigOptionTruthy("go_metrics")),
            ]
    """

    path: Path
    predicate: MetricsPredicate | None = None
