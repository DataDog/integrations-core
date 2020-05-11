# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import iteritems

from .common import is_metric, build_metric_to_submit
from ..constants import RESOURCE_TYPES


def parse_summary_status_resource_metrics(resource_type, data, tags):
    res_meta = RESOURCE_TYPES[resource_type]
    metrics = data['{}-status-list'.format(resource_type)]['status-list-summary']
    return _parse_status_metrics(res_meta['plural'], metrics, tags)


def parse_summary_status_base_metrics(data, tags):
    relations = data['local-cluster-status']['status-relations']
    for key, resource_data in iteritems(relations):
        if not key.endswith('-status'):
            continue
        resource_type = resource_data['typeref']
        metrics = resource_data['{}-status-summary'.format(resource_type)]
        # TODO: Ignore already collected metrics
        #       - forests-status-summary
        #       - hosts-status-summary
        #       - servers-status-summary
        for metric in _parse_status_metrics(resource_type, metrics, tags):
            yield metric


def _parse_status_metrics(metric_prefix, metrics, tags):
    for key, data in iteritems(metrics):
        if key in ['rate-properties', 'load-properties']:
            prop_type = key[:key.index('-properties')]
            total_key = 'total-' + prop_type
            yield build_metric_to_submit("{}.{}".format(metric_prefix, total_key), data[total_key], tags)
            for metric in _parse_status_metrics(metric_prefix, data[prop_type + '-detail'], tags):
                yield metric
        elif key == 'load-properties':
            yield build_metric_to_submit("{}.total-load".format(metric_prefix), data['total-load'], tags)
            for metric in _parse_status_metrics(metric_prefix, data['load-detail'], tags):
                yield metric
        elif is_metric(data):
            yield build_metric_to_submit("{}.{}".format(metric_prefix, key), data, tags)
