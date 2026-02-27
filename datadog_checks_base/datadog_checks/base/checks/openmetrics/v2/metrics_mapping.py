# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from datadog_checks.base.config import is_affirmative

if TYPE_CHECKING:
    from typing import Any, Mapping

RawMetricsConfig = dict[str, str | dict[str, str]]
"""Metric name mapping loaded from a YAML file.

Keys are raw Prometheus metric names, values are either Datadog metric names
(simple renaming) or dicts with ``name``, ``type``, etc. (full config).
"""


@runtime_checkable
class MetricsPredicate(Protocol):
    """
    Protocol for predicates that control whether a metrics mapping should be loaded.

    Implement ``should_load`` to create custom loading conditions.
    """

    def should_load(self, config: Mapping) -> bool: ...


class ConfigOptionTruthy:
    """
    Load metrics only if a configuration option is truthy.

    Uses ``is_affirmative`` to evaluate the value. Defaults to ``True``
    (include metrics unless explicitly disabled).
    """

    def __init__(self, option: str, default: bool = True) -> None:
        self.option = option
        self.default = default

    def should_load(self, config: Mapping) -> bool:
        return is_affirmative(config.get(self.option, self.default))


class ConfigOptionEquals:
    """
    Load metrics only if a configuration option equals a specific value.
    """

    def __init__(self, option: str, value: Any) -> None:
        self.option = option
        self.value = value

    def should_load(self, config: Mapping) -> bool:
        return config.get(self.option) == self.value


class AllOf:
    """
    Compose predicates: all must pass for the metrics to be loaded.

    Follows Python's ``all()`` semantics: returns ``True`` when empty.
    """

    def __init__(self, *predicates: MetricsPredicate) -> None:
        self.predicates = predicates

    def should_load(self, config: Mapping) -> bool:
        return all(p.should_load(config) for p in self.predicates)


class AnyOf:
    """
    Compose predicates: any passing is sufficient to load the metrics.

    Follows Python's ``any()`` semantics: returns ``False`` when empty.
    """

    def __init__(self, *predicates: MetricsPredicate) -> None:
        self.predicates = predicates

    def should_load(self, config: Mapping) -> bool:
        return any(p.should_load(config) for p in self.predicates)


@dataclass(frozen=True)
class MetricsMapping:
    """
    Declares a YAML file with metric name mappings to load automatically.

    Use in the ``METRICS_MAP`` class variable of ``OpenMetricsBaseCheckV2``
    subclasses. The YAML file should contain a flat mapping of Prometheus
    metric names to Datadog metric names::

        METRICS_MAP = [
            MetricsMapping(Path("metrics/default.yaml")),
            MetricsMapping(Path("metrics/go.yaml"), predicate=ConfigOptionTruthy("go_metrics")),
        ]
    """

    path: Path
    predicate: MetricsPredicate | None = None

    def should_load(self, config: Mapping) -> bool:
        """Return whether this mapping should be loaded for the given config."""
        return self.predicate is None or self.predicate.should_load(config)
