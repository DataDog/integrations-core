# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Containers from parsed metrics data.
"""

from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Pattern, Union  # noqa: F401

if TYPE_CHECKING:
    # needed to avoid circular import
    from .metrics import ColumnTag, IndexTag  # noqa: F401


class ParsedSymbolMetric(object):
    __slots__ = ('name', 'tags', 'forced_type', 'enforce_scalar', 'options', 'extract_value_pattern')

    def __init__(
        self,
        name,  # type: str
        tags=None,  # type: List[str]
        forced_type=None,  # type: str
        enforce_scalar=True,  # type: bool
        options=None,  # type: dict
        extract_value_pattern=None,  # type: Pattern
    ):
        # type: (...) -> None
        self.name = name
        self.tags = tags or []
        self.forced_type = forced_type
        self.enforce_scalar = enforce_scalar
        self.options = options or {}
        self.extract_value_pattern = extract_value_pattern


class ParsedTableMetric(object):
    __slots__ = ('name', 'index_tags', 'column_tags', 'forced_type', 'options', 'extract_value_pattern')

    def __init__(
        self,
        name,  # type: str
        index_tags,  # type: List[IndexTag]
        column_tags,  # type: List[ColumnTag]
        forced_type=None,  # type: str
        options=None,  # type: dict
        extract_value_pattern=None,  # type: Pattern
    ):
        # type: (...) -> None
        self.name = name
        self.index_tags = index_tags
        self.column_tags = column_tags
        self.forced_type = forced_type
        self.options = options or {}
        self.extract_value_pattern = extract_value_pattern


ParsedMetric = Union[ParsedSymbolMetric, ParsedTableMetric]


class ParsedSimpleMetricTag(object):
    __slots__ = ('name',)

    def __init__(self, name):
        # type: (str) -> None
        self.name = name

    def matched_tags(self, value):
        # type: (Any) -> Iterator[str]
        yield '{}:{}'.format(self.name, value)


class ParsedMatchMetricTag(object):
    __slots__ = ('tags', 'symbol', 'pattern')

    def __init__(self, tags, pattern):
        # type: (Dict[str, str], Pattern) -> None
        self.tags = tags
        self.pattern = pattern

    def matched_tags(self, value):
        # type: (Any) -> Iterator[str]
        match = self.pattern.match(str(value))
        if match is None:
            return

        for name, template in self.tags.items():
            yield '{}:{}'.format(name, match.expand(template))


ParsedMetricTag = Union[ParsedSimpleMetricTag, ParsedMatchMetricTag]
