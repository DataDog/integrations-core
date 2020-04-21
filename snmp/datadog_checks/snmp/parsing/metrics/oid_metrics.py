# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from ...models import OID
from ..parsed_metrics import ParsedSymbolMetric
from .models import ParseResult
from .types import OIDMetric


def parse_oid_metric(metric):
    # type: (OIDMetric) -> ParseResult
    name = metric['name']
    oid = OID(metric['OID'])

    parsed_symbol_metric = ParsedSymbolMetric(
        name, tags=metric.get('metric_tags', []), forced_type=metric.get('forced_type'), enforce_scalar=False
    )

    return ParseResult(oids_to_fetch=[oid], oids_to_resolve={name: oid}, parsed_metrics=[parsed_symbol_metric])
