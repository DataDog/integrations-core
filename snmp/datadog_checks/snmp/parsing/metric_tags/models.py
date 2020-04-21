# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from typing import Dict

from ...models import OID
from ..parsed_metrics import ParsedMetricTag


class MetricTagParseResult(object):
    def __init__(self, oid, parsed_metric_tag, oids_to_resolve=None):
        # type: (OID, ParsedMetricTag, Dict[str, OID]) -> None
        self.oid = oid
        self.parsed_metric_tag = parsed_metric_tag
        self.oids_to_resolve = oids_to_resolve or {}
