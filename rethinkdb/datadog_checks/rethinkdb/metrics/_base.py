# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from typing import (
    Any,
    Callable,
    ClassVar,
    Generic,
    Iterator,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    TypeVar,
    Union,
)

from datadog_checks.base import AgentCheck

from ..connections import Connection
from ..queries import QueryEngine
from ..types import Metric, MetricType
from ..utils import dotted_join, lookup_dotted, to_timestamp

logger = logging.getLogger(__name__)

T = TypeVar("T")
DocumentT = TypeVar("DocumentT", bound=Mapping)

ModifierName = Literal['total', 'ok_warning', 'timestamp']
TotalModifier = TypedDict('TotalModifier', {'name': Literal['total'], 'map': Callable[[Any], Sequence[T]]})
Modifier = Union[ModifierName, TotalModifier]

MetricDefinition = TypedDict(
    'MetricDefinition',
    {
        'type': MetricType,
        'path': str,  # Used as the default name.
        'name': str,  # An explicit name for the metric.
        'modifier': Optional[Modifier],
    },
    total=False,
)

Enumeration = TypedDict('Enumeration', {'path': str, 'index_tag': str, 'metrics': List[MetricDefinition]})


class DocumentMetricCollector(Generic[DocumentT]):
    """
    TODO(before-merging): Explain how to use this.
    """

    name = ''  # type: ClassVar[str]
    group = ''  # type: ClassVar[str]

    metrics = []  # type: ClassVar[List[MetricDefinition]]
    enumerations = []  # type: ClassVar[List[Enumeration]]

    def iter_documents(self, engine, conn):
        # type: (QueryEngine, Connection) -> Iterator[Tuple[DocumentT, List[str]]]
        raise NotImplementedError  # pragma: no cover

    def _make_metric(self, type, name, value, tags=None):
        # type: (MetricType, str, float, List[str]) -> Metric
        name = dotted_join(('rethinkdb', self.group, name))
        tags = [] if tags is None else tags
        return {'type': type, 'name': name, 'value': value, 'tags': tags}

    def _make_metric_from_definition(self, document, definition, tags):
        # type: (DocumentT, MetricDefinition, List[str]) -> Metric
        logger.debug('make_metric_from_definition definition=%r', definition)

        path = definition['path']
        name = definition.get('name', path)
        value = lookup_dotted(document, path=path)

        if 'modifier' in definition and definition['modifier'] is not None:
            value, suffix = self._modify(value, modifier=definition['modifier'])
            name = dotted_join((name, suffix), drop_empty=True)

        if not isinstance(value, (int, float)):
            raise RuntimeError('Expected float or int, got {!r} of type {}', value, type(value))

        return self._make_metric(type=definition['type'], name=name, value=value, tags=tags)

    def _make_metrics_from_enumeration(self, document, enumeration, tags):
        # type: (DocumentT, Enumeration, List[str]) -> Iterator[Metric]
        logger.debug('make_metrics_from_enumeration enumeration=%r', enumeration)

        values = lookup_dotted(document, path=enumeration['path'])  # type: Sequence
        index_tag = enumeration['index_tag']

        for index, value in enumerate(values):
            item_tags = tags + ['{}:{}'.format(index_tag, index)]
            for definition in enumeration['metrics']:
                definition = {
                    'type': definition['type'],
                    'name': dotted_join((enumeration['path'], definition['path']), drop_empty=True),
                    'path': definition['path'],
                    'modifier': definition.get('modifier'),
                }
                yield self._make_metric_from_definition(value, definition, tags=item_tags)

    def _modify(self, value, modifier):
        # type: (Any, Modifier) -> Tuple[float, str]
        logger.debug('modify value=%r modifier=%r', value, modifier)

        if modifier == 'total':
            return len(value), 'total'

        if modifier == 'ok_warning':
            return AgentCheck.OK if value else AgentCheck.WARNING, ''

        if modifier == 'timestamp':
            return to_timestamp(value), ''

        if isinstance(modifier, dict):
            if modifier['name'] == 'total':
                value = modifier['map'](value)
                return self._modify(value, modifier='total')

        raise RuntimeError('Unknown modifier: {!r}'.format(modifier))  # pragma: no cover

    def _collect(self, engine, conn):
        # type: (QueryEngine, Connection) -> Iterator[Metric]
        for document, tags in self.iter_documents(engine, conn):
            logger.debug('%s %r', self.name, document)

            for definition in self.metrics:
                yield self._make_metric_from_definition(document, definition, tags=tags)

            for enumeration in self.enumerations:
                for metric in self._make_metrics_from_enumeration(document, enumeration, tags=tags):
                    yield metric

    # Collection function implementation.

    def __call__(self, engine, conn):
        # type: (QueryEngine, Connection) -> Iterator[Metric]
        logger.debug('collect_%s', self.name)
        for metric in self._collect(engine, conn):
            yield metric
