# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Containers from parsed metrics data.
"""

from typing import Any, Dict, Iterator, List, Pattern, Tuple, Union


class ParsedSymbolMetric(object):
    __slots__ = ('name', 'tags', 'forced_type', 'enforce_scalar')

    def __init__(
        self,
        name,  # type: str
        tags=None,  # type: List[str]
        forced_type=None,  # type: str
        enforce_scalar=True,  # type: bool
    ):
        # type: (...) -> None
        self.name = name
        self.tags = tags or []
        self.forced_type = forced_type
        self.enforce_scalar = enforce_scalar


class ParsedTableMetric(object):
    __slots__ = ('name', 'index_tags', 'column_tags', 'forced_type')

    def __init__(
        self,
        name,  # type: str
        index_tags,  # type: List[Tuple[str, int]]
        column_tags,  # type: List[Tuple[str, str]]
        forced_type=None,  # type: str
    ):
        # type: (...) -> None
        self.name = name
        self.index_tags = index_tags
        self.column_tags = column_tags
        self.forced_type = forced_type


ParsedMetric = Union[ParsedSymbolMetric, ParsedTableMetric]


class ParsedSimpleMetricTag(object):
    __slots__ = ('name', 'symbol')

    def __init__(self, name, symbol):
        # type: (str, str) -> None
        self.name = name
        self.symbol = symbol

    def matched_tags(self, value):
        # type: (Any) -> Iterator[str]
        yield '{}:{}'.format(self.name, value)


class ParsedMatchMetricTag(object):
    __slots__ = ('tags', 'symbol', 'pattern')

    def __init__(self, tags, symbol, pattern):
        # type: (Dict[str, str], str, Pattern) -> None
        self.tags = tags
        self.symbol = symbol
        self.pattern = pattern

    def matched_tags(self, value):
        # type: (Any) -> Iterator[str]
        match = self.pattern.match(str(value))
        if match is None:
            return

        for name, template in self.tags.items():
            yield '{}:{}'.format(name, match.expand(template))


ParsedMetricTag = Union[ParsedSimpleMetricTag, ParsedMatchMetricTag]
