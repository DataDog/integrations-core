# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.datadog_agent.metrics import METRIC_MAP


class DatadogAgentCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'datadog.agent'

    DEFAULT_METRIC_LIMIT = 0

    def get_default_config(self):
        return {
            'metrics': [METRIC_MAP],
            # The forwarder telemetry has its own `endpoint` label (the intake endpoint), which would be ambiguous
            # alongside the scraped endpoint's URL.
            'tag_by_endpoint': False,
        }
