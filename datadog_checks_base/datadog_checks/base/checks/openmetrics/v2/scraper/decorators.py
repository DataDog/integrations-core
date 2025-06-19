# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING

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
        super().__init__(scraper.check, scraper.config)

    def consume_metrics(self, runtime_data) -> Generator[Metric]:
        for metric in self.scraper.consume_metrics(runtime_data):
            for sample in metric.samples:
                if (
                    (code := sample.labels.get(self.http_status_tag))
                    and isinstance(code, str)
                    and len(code) == 3
                    and code.isdigit()
                ):
                    sample.labels["code_class"] = f"{code[0]}xx"

            yield metric
