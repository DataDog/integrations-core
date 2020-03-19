# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Callable, Iterator, List, Mapping, Sequence, Tuple

from datadog_checks.base import AgentCheck
from datadog_checks.base.log import CheckLoggingAdapter

from .types import Enumeration, Group, Metric, MetricSpec, Modifier
from .utils import dotted_join, lookup_dotted, to_timestamp


class DocumentQuery(object):
    """
    A helper for retrieving metrics from document-oriented ("JSON") databases.
    """

    def __init__(
        self,
        source,  # type: Callable[..., Iterator[Tuple[Any, List[str]]]]
        name,  # type: str
        prefix,  # type: str
        metrics=None,  # type: List[MetricSpec]
        enumerations=None,  # type: List[Enumeration]
        groups=None,  # type: List[Group]
    ):
        self.source = source
        self.name = name
        self.prefix = prefix
        self.metrics = [] if metrics is None else metrics
        self.enumerations = [] if enumerations is None else enumerations
        self.groups = [] if groups is None else groups

    def _make_metric_from_spec(self, document, spec, tags, logger):
        # type: (Any, MetricSpec, List[str], CheckLoggingAdapter) -> Metric
        logger.trace('make_metric_from_spec %r', spec)

        path = spec['path']
        name = spec.get('name', path)
        value = lookup_dotted(document, path=path)

        if 'modifier' in spec and spec['modifier'] is not None:
            value = self._modify(value, modifier=spec['modifier'], logger=logger)

        if not isinstance(value, (int, float)):  # pragma: no cover
            raise RuntimeError('Expected float or int, got {!r} of type {}', value, type(value))

        name = dotted_join(('rethinkdb', self.prefix, name))

        return {'type': spec['type'], 'name': name, 'value': value, 'tags': tags}

    def _make_metrics_from_enumeration(self, document, enumeration, tags, logger):
        # type: (Any, Enumeration, List[str], CheckLoggingAdapter) -> Iterator[Metric]
        logger.trace('make_metrics_from_enumeration enumeration=%r', enumeration)

        values = lookup_dotted(document, path=enumeration['path'])  # type: Sequence

        for index, value in enumerate(values):
            item_tags = tags + ['{}:{}'.format(enumeration['index_tag'], index)]

            for spec in enumeration['metrics']:
                spec = {
                    'type': spec['type'],
                    'name': dotted_join((enumeration['path'], spec['path']), drop_empty=True),
                    'path': spec['path'],
                    'modifier': spec.get('modifier'),
                }
                yield self._make_metric_from_spec(value, spec, tags=item_tags, logger=logger)

    def _make_metrics_from_group(self, document, group, tags, logger):
        # type: (Any, Group, List[str], CheckLoggingAdapter) -> Iterator[Metric]
        logger.trace('make_metrics_from_group group=%r', group)

        mapping = lookup_dotted(document, path=group['path'])  # type: Mapping

        for key in mapping:
            item_tags = tags + ['{}:{}'.format(group['key_tag'], key)]
            spec = {
                'type': group['value_metric_type'],
                'name': group['path'],
                'path': key,
            }  # type: MetricSpec
            yield self._make_metric_from_spec(mapping, spec, tags=item_tags, logger=logger)

    def _modify(self, value, modifier, logger):
        # type: (Any, Modifier, CheckLoggingAdapter) -> float
        logger.trace('modify value=%r modifier=%r', value, modifier)

        if modifier == 'total':
            return len(value)

        if modifier == 'ok_warning':
            return AgentCheck.OK if value else AgentCheck.WARNING

        if modifier == 'timestamp':
            return to_timestamp(value)

        raise RuntimeError('Unknown modifier: {!r}'.format(modifier))  # pragma: no cover

    def run(self, *args, **kwargs):
        # type: (*Any, **Any) -> Iterator[Metric]
        logger = kwargs.pop('logger')  # type: CheckLoggingAdapter

        logger.debug('query_%s', self.name)

        for document, tags in self.source(*args, **kwargs):
            logger.debug('%s %r', self.name, document)

            for spec in self.metrics:
                yield self._make_metric_from_spec(document, spec, tags=tags, logger=logger)

            for enumeration in self.enumerations:
                for metric in self._make_metrics_from_enumeration(document, enumeration, tags=tags, logger=logger):
                    yield metric

            for group in self.groups:
                for metric in self._make_metrics_from_group(document, group, tags=tags, logger=logger):
                    yield metric
