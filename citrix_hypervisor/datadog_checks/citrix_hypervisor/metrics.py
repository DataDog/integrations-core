# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

SIMPLE_METRICS = {
    'cpu0': '.cpu',
    'memory': '.memory',
    'memory_reclaimed_max': '.memory.reclaimed_max',
    'memory_reclaimed': '.memory.reclaimed',
    'memory_total_kib': '.memory.total_kib',
    'memory_free_kib': '.memory.free_kib',
    'pool_task_count': '.pool.task_count',
    'pool_session_count': '.pool.session_count',
    'xapi_memory_usage_kib': '.xapi.memory_usage_kib',
    'xapi_free_memory_kib': '.xapi.free_memory_kib',
    'xapi_live_memory_kib': '.xapi.live_memory_kib',
    'xapi_allocation_kib': '.xapi.allocation_kib',
}

REGEX_METRICS = [
    {'regex': 'sr_([a-z0-9-]+)_cache_misses', 'name': '.cache_misses', 'tags': ('cache_sr',)},
    {'regex': 'sr_([a-z0-9-]+)_cache_hits', 'name': '.cache_hits', 'tags': ('cache_sr',)},
    {'regex': 'sr_([a-z0-9-]+)_cache_size', 'name': '.cache_size', 'tags': ('cache_sr',)},
]

METRICS_SUFFIX = {
    'AVERAGE': '.avg',
    'MAX': '.max',
    'MIN': '.min',
}


def build_metric(metric_name, logger):
    """
    "AVERAGE:host:1e108be9-8ad0-4988-beff-03d8bb1369ae:sr_35c781cf-951d-0456-8190-373e3c08193e_cache_misses"
    "AVERAGE:vm:057d0e50-da57-4fde-b0a7-9ebd1bf42a59:memory"
    """
    metric_parts = metric_name.split(':')

    if len(metric_parts) != 4:
        logger.debug('Unknown format for metric %s', metric_name)
        return None, None

    name = metric_parts[1]
    additional_tags = ['citrix_hypervisor_{}:{}'.format(metric_parts[1], metric_parts[2])]
    found = False

    if SIMPLE_METRICS.get(metric_parts[-1]):
        name += SIMPLE_METRICS[metric_parts[-1]]
    else:
        found = False
        for regex in REGEX_METRICS:
            tags_values = re.findall(regex['regex'], metric_name)

            if len(tags_values) > 0 and isinstance(tags_values[0], tuple):
                tags_values = tags_values[0]

            if len(tags_values) == len(regex['tags']):
                found = True
                name += regex['name']
                for i in range(len(regex['tags'])):
                    additional_tags.append('{}:{}'.format(regex['tags'][i], tags_values[i]))
                break

        if not found:
            logger.debug('Ignoring metric %s', metric_name)
            return None, None

    name += METRICS_SUFFIX[metric_parts[0]]

    logger.debug('Found metric %s (%s)', name, metric_name)

    return (name, additional_tags)
