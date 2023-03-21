# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import List  # noqa: F401

from datadog_checks.base import ConfigurationError
from datadog_checks.base.types import InstanceType  # noqa: F401

from .metrics import EDGE_AGENT_METRICS, EDGE_AGENT_TYPE_OVERRIDES, EDGE_HUB_METRICS
from .types import Instance  # noqa: F401


class Config(object):
    """
    Hold instance configuration for a check.

    Encapsulates the validation of an `instance` dictionary while improving type information.
    """

    def __init__(self, instance):
        # type: (Instance) -> None
        tags = instance.get('tags', [])

        if not isinstance(tags, list):
            raise ConfigurationError('tags {!r} must be a list (got {!r})'.format(tags, type(tags)))

        edge_hub_prometheus_url = instance.get('edge_hub_prometheus_url')
        if not edge_hub_prometheus_url:
            raise ConfigurationError('option "edge_hub_prometheus_url" is required')

        edge_hub_instance = self._create_prometheus_instance(
            edge_hub_prometheus_url, namespace='edge_hub', metrics=EDGE_HUB_METRICS, tags=tags
        )

        edge_agent_prometheus_url = instance.get('edge_agent_prometheus_url')
        if not edge_agent_prometheus_url:
            raise ConfigurationError('option "edge_agent_prometheus_url" is required')

        edge_agent_instance = self._create_prometheus_instance(
            edge_agent_prometheus_url, namespace='edge_agent', metrics=EDGE_AGENT_METRICS, tags=tags
        )
        edge_agent_instance['type_overrides'] = EDGE_AGENT_TYPE_OVERRIDES

        # Configure version metadata collection.
        edge_agent_instance['metadata_metric_name'] = 'edgeAgent_metadata'
        edge_agent_instance['metadata_label_map'] = {'version': 'edge_agent_version'}

        self.prometheus_instances = [
            edge_hub_instance,
            edge_agent_instance,
        ]

    def _create_prometheus_instance(self, url, namespace, metrics, tags):
        # type: (str, str, list, List[str]) -> InstanceType
        return {
            'prometheus_url': url,
            'namespace': namespace,
            'metrics': metrics,
            'tags': tags,
            'exclude_labels': [
                'ms_telemetry',  # Always 'True'.
                'instance_number',  # Random GUID, changes on device restart (risk of context explosion).
            ],
        }
