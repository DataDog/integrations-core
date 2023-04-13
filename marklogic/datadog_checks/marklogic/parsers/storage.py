# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict, Generator, List, Tuple  # noqa: F401

from six import iteritems

from .common import build_metric_to_submit, is_metric


def parse_summary_storage_base_metrics(data, tags):
    # type: (Dict[str, Any], List[str]) -> Generator[Tuple, None, None]
    return _parse_storage_metrics(data, tags, include_location_forest=True)


def parse_per_resource_storage_metrics(data, tags):
    # type: (Dict[str, Any], List[str]) -> Generator[Tuple, None, None]
    return _parse_storage_metrics(data, tags, include_location_forest=False)


def _parse_storage_metrics(data, tags, include_location_forest):
    # type: (Dict[str, Any], List[str], bool) -> Generator[Tuple, None, None]
    """
    Collect Base Storage Metrics
    """
    hosts_meta = {}
    relations = data['forest-storage-list']['relations']['relation-group']
    for rel in relations:
        if rel['typeref'] == 'hosts':
            for host in rel['relation']:
                hosts_meta[host['idref']] = host['nameref']

    all_hosts_data = data['forest-storage-list']['storage-list-items']['storage-host']

    for host_data in all_hosts_data:
        host_tags = tags[:]
        host_id = host_data['relation-id']
        host_tags.append('marklogic_host_id:{}'.format(host_id))
        host_tags.append('marklogic_host_name:{}'.format(hosts_meta[host_id]))
        for location_data in host_data['locations']['location']:
            location_tags = host_tags + ['storage_path:{}'.format(location_data['path'])]
            for host_key, host_value in iteritems(location_data):
                if host_key == 'location-forests':
                    location_value = host_value['location-forest']
                    for forest_data in location_value:
                        forest_tags = location_tags + [
                            "forest_id:{}".format(forest_data['idref']),
                            "forest_name:{}".format(forest_data['nameref']),
                        ]
                        if include_location_forest:
                            for forest_key, forest_value in iteritems(forest_data):
                                if forest_key == 'disk-size':
                                    metric = build_metric_to_submit(
                                        "forests.storage.{}".format(forest_key), forest_value, tags=forest_tags
                                    )
                                    if metric is not None:
                                        yield metric
                elif is_metric(host_value):
                    metric = build_metric_to_submit(
                        "forests.storage.host.{}".format(host_key), host_value, tags=location_tags
                    )
                    if metric is not None:
                        yield metric
