# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from typing import Any, Callable, Iterable, Iterator, List, Mapping, Sequence, Tuple, Union

from .types import Enumeration, Group, Metric, MetricSpec
from .utils import dotted_join, lookup_dotted, null_logger


class DocumentQuery(object):
    """
    A generic helper for retrieving metrics from document-oriented ("JSON") databases.

    Example
    -------
    See:
    https://github.com/DataDog/integrations-core/blob/master/rethinkdb/datadog_checks/rethinkdb/document_db/_example.py

    Parameters
    ----------
    source:
        A callable that returns an iterable of `(document, tags)` pairs.
        * Should accept the same `**kwargs` than what will be passed to `.run()`.
        * `tags` will be applied to all metrics built from the corresponding `document`.
        * All documents should have the same structure.
    name:
        A verbose name for the query, for logging purposes. Example: `'memory_usage'`.
    prefix:
        Will be prepended to all metric names. Example: `'my_integration.memory'`.
    metrics:
        Each item in this list corresponds to a metric that will be submitted to Datadog.
        * `type` (required): metric type. Example: `'gauge'`.
        * `path` (required): dotted path to the value of interest in a `document`. Example: `'memory_usage.memory_mb'`.
        * `name`: an explicit metric name. If not set, the `path` is used. Example: `'memory_consumption'`.
        * `transformer`: a callable applied to metric values before submission. See `document_db.transformers` for
          built-in transformers.
    enumerations:
        Each item in this list corresponds to a set of metrics built from items in a JSON array.
        The name comes from the `enumerate()` Python built-in, as enumerations allow tagging by index in the array.
        * `path` (required): dotted path to the array of interest in a `document`.
        * `index_tag` (required): indexes will be attached as this tag. Example: `'cpu_position'`.
        * `metrics` (required): a list of metrics -- same structure as the `metrics` parameter. One copy will be
        submitted for each item in the array. The enumeration `path` is automatically prepended to each metric `path`.
    groups:
        Each item in this list corresponds to a metric built from a JSON object (mapping) that represents aggregated
        results, such as those returned by a GROUP BY operation. One copy of the metric will be submitted for each
        key/value item in the mapping.
        Keys:
        * `path` (required): dotted path to the mapping of interest in a `document`.
        * `key_tag` (required): keys of the mapping will be submitted as this tag. Example: `'country'`.
        * `value_type` (required): metric type of values in the mapping. Example: `'gauge'`.
    """

    def __init__(
        self,
        source,  # type: Callable[..., Iterable[Tuple[Any, List[str]]]]
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

    def _make_metric_from_spec(self, document, spec, tags):
        # type: (Any, MetricSpec, List[str]) -> Metric
        path = spec['path']
        name = spec.get('name', path)
        value = lookup_dotted(document, path=path)

        if 'transformer' in spec and spec['transformer'] is not None:
            value = spec['transformer'](value)

        if not isinstance(value, (int, float)):  # pragma: no cover
            raise RuntimeError('Expected float or int, got {!r} of type {}', value, type(value))

        name = dotted_join((self.prefix, name))

        return {'type': spec['type'], 'name': name, 'value': value, 'tags': tags}

    def _make_metrics_from_enumeration(self, document, enumeration, tags):
        # type: (Any, Enumeration, List[str]) -> Iterator[Metric]
        values = lookup_dotted(document, path=enumeration['path'])  # type: Sequence

        for index, value in enumerate(values):
            item_tags = tags + ['{}:{}'.format(enumeration['index_tag'], index)]

            for spec in enumeration['metrics']:
                spec = spec.copy()
                spec['name'] = dotted_join((enumeration['path'], spec['path']))
                yield self._make_metric_from_spec(value, spec, tags=item_tags)

    def _make_metrics_from_group(self, document, group, tags):
        # type: (Any, Group, List[str]) -> Iterator[Metric]
        mapping = lookup_dotted(document, path=group['path'])  # type: Mapping

        for key in mapping:
            item_tags = tags + ['{}:{}'.format(group['key_tag'], key)]
            spec = {
                'type': group['type'],
                'name': group['path'],
                'path': key,
            }  # type: MetricSpec
            yield self._make_metric_from_spec(mapping, spec, tags=item_tags)

    def run(self, logger=None, **kwargs):
        # type: (Union[logging.Logger, logging.LoggerAdapter], **Any) -> Iterator[Metric]
        if logger is None:
            logger = null_logger  # For convenience in unit tests and example scripts.

        logger.debug('document_query %s', self.name)

        for document, tags in self.source(**kwargs):
            logger.debug('%s %r', self.name, document)

            for spec in self.metrics:
                yield self._make_metric_from_spec(document, spec, tags=tags)

            for enumeration in self.enumerations:
                for metric in self._make_metrics_from_enumeration(document, enumeration, tags=tags):
                    yield metric

            for group in self.groups:
                for metric in self._make_metrics_from_group(document, group, tags=tags):
                    yield metric
