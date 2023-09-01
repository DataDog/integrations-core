# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import namedtuple

from six.moves.urllib.parse import urlparse

from datadog_checks.base import ConfigurationError, is_affirmative

ESInstanceConfig = namedtuple(
    'ESInstanceConfig',
    [
        'admin_forwarder',
        'pshard_stats',
        'pshard_graceful_to',
        'node_name_as_host',
        'cluster_stats',
        'detailed_index_stats',
        'slm_stats',
        'index_stats',
        'service_check_tags',
        'tags',
        'url',
        'pending_task_stats',
        'cat_allocation_stats',
        'custom_queries',
        'submit_events',
    ],
)


def from_instance(instance):
    """
    Create a config object from an instance dictionary
    """
    url = instance.get('url')
    if not url:
        raise ConfigurationError("A URL must be specified in the instance")

    pshard_stats = is_affirmative(instance.get('pshard_stats', False))
    pshard_graceful_to = is_affirmative(instance.get('pshard_graceful_timeout', False))
    node_name_as_host = is_affirmative(instance.get('node_name_as_host', False))
    index_stats = is_affirmative(instance.get('index_stats', False))
    cluster_stats = is_affirmative(instance.get('cluster_stats', False))
    detailed_index_stats = is_affirmative(instance.get('detailed_index_stats', False))
    slm_stats = is_affirmative(instance.get('slm_stats', False))
    if 'is_external' in instance:
        cluster_stats = is_affirmative(instance.get('is_external', False))
    pending_task_stats = is_affirmative(instance.get('pending_task_stats', True))
    admin_forwarder = is_affirmative(instance.get('admin_forwarder', False))
    cat_allocation_stats = is_affirmative(instance.get('cat_allocation_stats', False))

    # Support URLs that have a path in them from the config, for
    # backwards-compatibility.
    parsed = urlparse(url)
    if parsed[2] and not admin_forwarder:
        url = '{}://{}'.format(parsed[0], parsed[1])
    port = parsed.port
    host = parsed.hostname

    custom_tags = instance.get('tags', [])
    service_check_tags = ['host:{}'.format(host), 'port:{}'.format(port)]
    service_check_tags.extend(custom_tags)

    custom_queries = instance.get('custom_queries', [])

    submit_events = is_affirmative(instance.get('submit_events', True))

    # Tag by URL so we can differentiate the metrics
    # from multiple instances
    tags = ['url:{}'.format(url)]
    tags.extend(custom_tags)

    config = ESInstanceConfig(
        admin_forwarder=admin_forwarder,
        pshard_stats=pshard_stats,
        pshard_graceful_to=pshard_graceful_to,
        node_name_as_host=node_name_as_host,
        cluster_stats=cluster_stats,
        detailed_index_stats=detailed_index_stats,
        slm_stats=slm_stats,
        index_stats=index_stats,
        service_check_tags=service_check_tags,
        tags=tags,
        url=url,
        pending_task_stats=pending_task_stats,
        cat_allocation_stats=cat_allocation_stats,
        custom_queries=custom_queries,
        submit_events=submit_events,
    )
    return config
