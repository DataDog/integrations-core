# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any

from .base_scraper import OpenMetricsScraper

if TYPE_CHECKING:
    from collections.abc import Generator

    from prometheus_client.metrics_core import Metric


class WithHttpCodeClass(OpenMetricsScraper):
    """
    Scraper decorator that parses the HTTP status code from the metric and adds a new tag named
    `code_class` to the metric.

    The HTTP status code is parsed and a new tag named `code_class` is added to the metric
    stating whether the status code is in the 1xx, 2xx, 3xx, 4xx, or 5xx range.
    """

    def __init__(self, scraper: OpenMetricsScraper, http_status_tag: str):
        self.scraper = scraper
        self.http_status_tag = http_status_tag
        self.decorated_methods = {"yield_metrics": self.yield_metrics}

    def __getattr__(self, name: str) -> Any:
        return self.decorated_methods.get(name, getattr(self.scraper, name))

    def _add_http_code_class(self, metric: Metric, http_status_tag: str) -> Metric:
        for sample in metric.samples:
            if (
                (code := sample.labels.get(http_status_tag))
                and isinstance(code, str)
                and len(code) == 3
                and code.isdigit()
            ):
                sample.labels["code_class"] = f"{code[0]}xx"
        return metric

    def yield_metrics(self, runtime_data: dict[str, Any]) -> Generator[Metric]:
        add_http_code_class_func = partial(self._add_http_code_class, http_status_tag=self.http_status_tag)
        yield from map(add_http_code_class_func, self.scraper.yield_metrics(runtime_data))
