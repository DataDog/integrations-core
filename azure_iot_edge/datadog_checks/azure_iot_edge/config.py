# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import List

from datadog_checks.base import ConfigurationError
from datadog_checks.base.types import InstanceType

from .metrics import EDGE_AGENT_METRICS, EDGE_HUB_METRICS
from .types import Instance


class Config(object):
    """
    Hold instance configuration for a check.

    Encapsulates the validation of an `instance` dictionary while improving type information.
    """

    def __init__(self, instance, check_namespace):
        # type: (Instance, str) -> None
        self._check_namespace = check_namespace

        tags = instance.get('tags', [])

        if not isinstance(tags, list):
            raise ConfigurationError('tags {!r} must be a list (got {!r})'.format(tags, type(tags)))

        self.tags = tags  # type: List[str]

        self.security_daemon_management_api_url = instance.get('security_daemon_management_api_url')

        self.edge_hub_instance = self._create_prometheus_instance(
            instance, namespace='edge_hub', metrics=EDGE_HUB_METRICS
        )
        self.edge_agent_instance = self._create_prometheus_instance(
            instance, namespace='edge_agent', metrics=EDGE_AGENT_METRICS
        )

    def _create_prometheus_instance(self, instance, namespace, metrics):
        # type: (Instance, str, list) -> InstanceType
        config = instance['edge_hub'] if namespace == 'edge_hub' else instance['edge_agent']
        if config is None:
            raise ConfigurationError('Key {!r} is required'.format(namespace))

        endpoint = config.get('prometheus_url')
        if endpoint is None:
            raise ConfigurationError('{}: key "prometheus_url" is missing'.format(namespace))

        tags = instance.get('tags', [])

        return {
            'prometheus_url': endpoint,
            # NOTE: `__NAMESPACE__` is not honored by the OpenMetricsBaseCheck, so we have to insert it manually.
            'namespace': '{}.{}'.format(self._check_namespace, namespace),
            'metrics': metrics,
            'tags': tags,
            'exclude_labels': [
                'ms_telemetry',  # Always 'True'.
                'instance_number',  # Random GUID, changes on device restart (risk of context explosion).
            ],
        }
