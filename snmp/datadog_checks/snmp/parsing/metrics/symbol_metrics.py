# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from ..parsed_metrics import ParsedSymbolMetric
from .models import ParseResult
from .symbols import parse_symbol
from .types import SymbolMetric


def parse_symbol_metric(metric):
    # type: (SymbolMetric) -> ParseResult
    """
    Parse a symbol metric, given by a MIB name and a symbol string or object.
    """
    mib = metric['MIB']
    symbol = metric['symbol']

    parsed_symbol = parse_symbol(mib, symbol)

    parsed_symbol_metric = ParsedSymbolMetric(
        parsed_symbol.name, tags=metric.get('metric_tags', []), forced_type=metric.get('forced_type')
    )

    return ParseResult(
        oids_to_fetch=[parsed_symbol.oid],
        oids_to_resolve=parsed_symbol.oids_to_resolve,
        parsed_metrics=[parsed_symbol_metric],
    )
