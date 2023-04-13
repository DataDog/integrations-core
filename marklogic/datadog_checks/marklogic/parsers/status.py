# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict, Generator, List, Tuple  # noqa: F401

from six import iteritems

from ..constants import RESOURCE_TYPES
from .common import build_metric_to_submit, is_metric


def parse_summary_status_resource_metrics(resource_type, data, tags):
    #  type: (str, Dict, List[str]) -> Generator[Tuple, None, None]
    res_meta = RESOURCE_TYPES[resource_type]
    metrics = data['{}-status-list'.format(resource_type)]['status-list-summary']
    return _parse_status_metrics(res_meta['plural'], metrics, tags)


def parse_per_resource_status_metrics(resource_type, data, tags):
    #  type: (str, Dict[str, Any], List[str]) -> Generator[Tuple, None, None]
    res_meta = RESOURCE_TYPES[resource_type]
    metrics = data['{}-status'.format(resource_type)]['status-properties']
    return _parse_status_metrics(res_meta['plural'], metrics, tags)


def parse_summary_status_base_metrics(data, tags):
    #  type: (Dict[str, Any], List[str]) -> Generator[Tuple, None, None]
    relations = data['local-cluster-status']['status-relations']
    for key, resource_data in iteritems(relations):
        if not key.endswith('-status'):
            continue
        resource_type = resource_data['typeref']
        # Ignore already collected metrics
        #       - forests-status-summary
        if resource_type not in ['forests']:
            metrics = resource_data['{}-status-summary'.format(resource_type)]
            for metric in _parse_status_metrics(resource_type, metrics, tags):
                yield metric


def _parse_status_metrics(metric_prefix, metrics, tags):
    #  type: (str, Dict[str, Any], List[str]) -> Generator[Tuple, None, None]
    for key, data in iteritems(metrics):
        if key in ['rate-properties', 'load-properties']:
            prop_type = key[: key.index('-properties')]
            total_key = 'total-' + prop_type
            m = build_metric_to_submit("{}.{}".format(metric_prefix, total_key), data[total_key], tags)
            if m is not None:
                yield m
            for metric in _parse_status_metrics(metric_prefix, data[prop_type + '-detail'], tags):
                yield metric
        elif key == 'cache-properties':
            for metric in _parse_status_metrics(metric_prefix, data, tags):
                yield metric
        elif is_metric(data):
            m = build_metric_to_submit("{}.{}".format(metric_prefix, key), data, tags)
            if m is not None:
                yield m
