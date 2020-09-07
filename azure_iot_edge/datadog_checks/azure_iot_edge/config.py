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

        security_daemon_management_api_url = instance.get('security_daemon_management_api_url')
        if not security_daemon_management_api_url:
            raise ConfigurationError('option "security_daemon_management_api_url" is required')

        self.security_daemon_management_api_url = security_daemon_management_api_url

        edge_hub_prometheus_url = instance.get('edge_hub_prometheus_url')
        if not edge_hub_prometheus_url:
            raise ConfigurationError('option "edge_hub_prometheus_url" is required')

        self.edge_hub_instance = self._create_prometheus_instance(
            edge_hub_prometheus_url, namespace='edge_hub', metrics=EDGE_HUB_METRICS, tags=self.tags
        )

        edge_agent_prometheus_url = instance.get('edge_agent_prometheus_url')
        if not edge_agent_prometheus_url:
            raise ConfigurationError('option "edge_agent_prometheus_url" is required')

        self.edge_agent_instance = self._create_prometheus_instance(
            edge_agent_prometheus_url, namespace='edge_agent', metrics=EDGE_AGENT_METRICS, tags=self.tags
        )

    def _create_prometheus_instance(self, url, namespace, metrics, tags):
        # type: (str, str, list, List[str]) -> InstanceType
        return {
            'prometheus_url': url,
            # NOTE: `__NAMESPACE__` is not honored by the OpenMetricsBaseCheck, so we have to insert it manually.
            'namespace': '{}.{}'.format(self._check_namespace, namespace),
            'metrics': metrics,
            'tags': tags,
            'exclude_labels': [
                'ms_telemetry',  # Always 'True'.
                'instance_number',  # Random GUID, changes on device restart (risk of context explosion).
            ],
        }
