# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from datadog_checks.base.config import is_affirmative

if TYPE_CHECKING:
    from datadog_checks.base.types import InstanceType

_RawMetricsConfig = dict[str, str | dict[str, Any]]
"""Metric name mapping loaded from a YAML file.

Keys are raw Prometheus metric names; values are either Datadog metric names
(simple renaming) or dicts describing transformer configuration. The inner
dict carries the full ``OpenMetricsScraper`` transformer shape (type, label
maps, nested options), so it is intentionally widened to ``dict[str, Any]``.

Internal: the type the loader returns; integration authors should not need to
reference this directly.
"""


class MetricsPredicate(Protocol):
    """
    Protocol for conditional metrics loading.

    Any class with a ``should_load(self, config) -> bool`` method satisfies
    this protocol and can be used as a predicate in ``MetricsMapping``. No
    inheritance or registration is required.
    """

    def should_load(self, config: InstanceType) -> bool: ...


class ConfigOptionTruthy:
    """
    Load metrics when a config option is truthy; skip when it is falsy.

    Uses ``is_affirmative`` to evaluate the option value. When the option is
    absent from the config, ``default`` is used (``True`` by default, so
    metrics are included unless explicitly disabled).

    Args:
        option: The instance config key to evaluate.
        default: Fallback value when the option is not present.
    """

    def __init__(self, option: str, default: bool = True) -> None:
        self.option = option
        self.default = default

    def should_load(self, config: InstanceType) -> bool:
        return is_affirmative(config.get(self.option, self.default))


class ConfigOptionEquals:
    """
    Load metrics when a config option equals a specific value; skip otherwise.

    A missing key compares equal to ``None``: ``ConfigOptionEquals("flag", None)``
    matches both ``{"flag": None}`` and instances that omit the key entirely.

    Args:
        option: The instance config key to evaluate.
        value: The exact value the option must equal.
    """

    def __init__(self, option: str, value: Any) -> None:
        self.option = option
        self.value = value

    def should_load(self, config: InstanceType) -> bool:
        return config.get(self.option) == self.value


class AllOf:
    """
    Conjunction of predicates; all must pass for the metrics to be loaded.

    Follows Python's ``all()`` semantics: returns ``True`` when given no
    predicates.

    Args:
        predicates: One or more ``MetricsPredicate`` instances to evaluate.
    """

    def __init__(self, *predicates: MetricsPredicate) -> None:
        self.predicates = predicates

    def should_load(self, config: InstanceType) -> bool:
        return all(p.should_load(config) for p in self.predicates)


class AnyOf:
    """
    Disjunction of predicates; any one passing is sufficient to load the metrics.

    Follows Python's ``any()`` semantics: returns ``False`` when given no
    predicates.

    Args:
        predicates: One or more ``MetricsPredicate`` instances to evaluate.
    """

    def __init__(self, *predicates: MetricsPredicate) -> None:
        self.predicates = predicates

    def should_load(self, config: InstanceType) -> bool:
        return any(p.should_load(config) for p in self.predicates)


@dataclass(frozen=True)
class MetricsMapping:
    """
    Declares a single YAML file containing metric name mappings to load automatically.

    Use in the ``METRICS_MAP`` class variable of ``OpenMetricsBaseCheckV2``
    subclasses. The path is relative to the package directory. An optional
    predicate controls whether the file is loaded for a given instance config;
    when omitted, the file is always loaded.

    Example::

        METRICS_MAP = (
            MetricsMapping(Path("metrics/default.yaml")),
            MetricsMapping(Path("metrics/go.yaml"), predicate=ConfigOptionTruthy("go_metrics")),
        )

    Args:
        path: Path to the YAML metrics file, relative to the package directory.
        predicate: Optional condition that gates loading. Defaults to always load.
    """

    path: Path
    predicate: MetricsPredicate | None = None

    def should_load(self, config: InstanceType) -> bool:
        """Return whether this mapping should be loaded for the given config."""
        return self.predicate is None or self.predicate.should_load(config)
