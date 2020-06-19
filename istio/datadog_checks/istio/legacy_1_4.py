# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from copy import deepcopy

from datadog_checks.base import OpenMetricsBaseCheck
from datadog_checks.base.errors import CheckException

from .constants import (
    BLACKLIST_LABELS,
    CITADEL_NAMESPACE,
    GALLEY_NAMESPACE,
    MESH_NAMESPACE,
    MIXER_NAMESPACE,
    PILOT_NAMESPACE,
)
from .metrics import CITADEL_METRICS, GALLEY_METRICS, GENERIC_METRICS, MESH_METRICS, MIXER_METRICS, PILOT_METRICS


class LegacyIstioCheck_1_4(OpenMetricsBaseCheck):

    DEFAULT_METRIC_LIMIT = 0
    SOURCE_TYPE_NAME = 'istio'

    def __init__(self, name, init_config, instances):

        # Create instances we can use in OpenMetricsBaseCheck
        generic_instances = None
        if instances is not None:
            generic_instances = self.create_generic_instances(instances)

        # Set up OpenMetricsBaseCheck with our generic instances
        super(LegacyIstioCheck_1_4, self).__init__(name, init_config, generic_instances)

    def check(self, instance):
        """
        Process all the endpoints associated with this instance.
        All the endpoints themselves are optional, but at least one must be passed.
        """
        processed = False
        # Get the config for the istio_mesh instance
        istio_mesh_endpoint = instance.get('istio_mesh_endpoint')
        if istio_mesh_endpoint:
            istio_mesh_config = self.config_map[istio_mesh_endpoint]

            # Process istio_mesh
            self.process(istio_mesh_config)
            processed = True

        # Get the config for the process_mixer instance
        process_mixer_endpoint = instance.get('mixer_endpoint')
        if process_mixer_endpoint:
            process_mixer_config = self.config_map[process_mixer_endpoint]

            # Process process_mixer
            self.process(process_mixer_config)
            processed = True

        # Get the config for the process_pilot instance
        process_pilot_endpoint = instance.get('pilot_endpoint')
        if process_pilot_endpoint:
            process_pilot_config = self.config_map[process_pilot_endpoint]

            # Process process_pilot
            self.process(process_pilot_config)
            processed = True

        # Get the config for the process_galley instance
        process_galley_endpoint = instance.get('galley_endpoint')
        if process_galley_endpoint:
            process_galley_config = self.config_map[process_galley_endpoint]

            # Process process_galley
            self.process(process_galley_config)
            processed = True

        # Get the config for the process_citadel instance
        process_citadel_endpoint = instance.get('citadel_endpoint')
        if process_citadel_endpoint:
            process_citadel_config = self.config_map[process_citadel_endpoint]

            # Process process_citadel
            self.process(process_citadel_config)
            processed = True

        # Check that at least 1 endpoint is configured
        if not processed:
            raise CheckException("At least one of Mixer, Mesh, Pilot, Galley or Citadel endpoints must be configured")

    def create_generic_instances(self, instances):
        """
        Generalize each (single) Istio instance into OpenMetricsBaseCheck instances.
        """
        result = []
        for instance in instances:
            exclude_labels = instance.get('exclude_labels', []) + BLACKLIST_LABELS
            instance.update({'exclude_labels': exclude_labels})

            if 'istio_mesh_endpoint' in instance:
                result.append(self._create_istio_mesh_instance(instance))
            if 'mixer_endpoint' in instance:
                result.append(self._create_process_mixer_instance(instance))
            if 'pilot_endpoint' in instance:
                result.append(self._create_process_pilot_instance(instance))
            if 'galley_endpoint' in instance:
                result.append(self._create_process_galley_instance(instance))
            if 'citadel_endpoint' in instance:
                result.append(self._create_process_citadel_instance(instance))
        return result

    def _create_istio_mesh_instance(self, instance):
        """
        Grab the istio mesh scraper from the dict and return it if it exists,
        otherwise create the scraper and add it to the dict.
        """
        endpoint = instance.get('istio_mesh_endpoint')

        istio_mesh_instance = deepcopy(instance)
        istio_mesh_instance.update(
            {
                'namespace': MESH_NAMESPACE,
                'prometheus_url': endpoint,
                'label_to_hostname': endpoint,
                'metrics': [MESH_METRICS],
                # Defaults that were set when istio was based on PrometheusCheck
                'send_monotonic_counter': instance.get('send_monotonic_counter', False),
                'health_service_check': instance.get('health_service_check', False),
                # Override flag to submit monotonic_count for Prometheus counter metrics along with gauge.
                # This allows backwards compatibility for the overriding of `send_monotonic_counter`
                # in order to submit correct metric types. Monotonic counter metrics end with `.total` to its gauge
                'send_monotonic_with_gauge': instance.get('send_monotonic_with_gauge', True),
            }
        )

        return istio_mesh_instance

    def _create_process_mixer_instance(self, instance):
        """
        Grab the mixer scraper from the dict and return it if it exists,
        otherwise create the scraper and add it to the dict.
        """
        endpoint = instance.get('mixer_endpoint')

        process_mixer_instance = deepcopy(instance)
        MIXER_METRICS.update(GENERIC_METRICS)
        process_mixer_instance.update(
            {
                'namespace': MIXER_NAMESPACE,
                'prometheus_url': endpoint,
                'metrics': [MIXER_METRICS],
                # Defaults that were set when istio was based on PrometheusCheck
                'send_monotonic_counter': instance.get('send_monotonic_counter', False),
                'health_service_check': instance.get('health_service_check', False),
            }
        )
        return process_mixer_instance

    def _create_process_pilot_instance(self, instance):
        """
        Grab the pilot scraper from the dict and return it if it exists,
        otherwise create the scraper and add it to the dict.
        """
        endpoint = instance.get('pilot_endpoint')

        process_pilot_instance = deepcopy(instance)
        PILOT_METRICS.update(GENERIC_METRICS)
        process_pilot_instance.update(
            {'namespace': PILOT_NAMESPACE, 'prometheus_url': endpoint, 'metrics': [PILOT_METRICS]}
        )
        return process_pilot_instance

    def _create_process_galley_instance(self, instance):
        """
        Grab the galley scraper from the dict and return it if it exists,
        otherwise create the scraper and add it to the dict.
        """
        endpoint = instance.get('galley_endpoint')

        process_galley_instance = deepcopy(instance)
        GALLEY_METRICS.update(GENERIC_METRICS)
        process_galley_instance.update(
            {
                'namespace': GALLEY_NAMESPACE,
                'prometheus_url': endpoint,
                'metrics': [GALLEY_METRICS],
                # The following metrics have been blakclisted due to high cardinality of tags
                'ignore_metrics': ['galley_mcp_source_message_size_bytes', 'galley_mcp_source_request_acks_total'],
            }
        )
        process_galley_instance['ignore_metrics'].extend(instance.get('ignore_metrics', []))
        return process_galley_instance

    def _create_process_citadel_instance(self, instance):
        """
        Grab the citadel scraper from the dict and return it if it exists,
        otherwise create the scraper and add it to the dict.
        """
        endpoint = instance.get('citadel_endpoint')

        process_citadel_instance = deepcopy(instance)
        CITADEL_METRICS.update(GENERIC_METRICS)
        process_citadel_instance.update(
            {'namespace': CITADEL_NAMESPACE, 'prometheus_url': endpoint, 'metrics': [CITADEL_METRICS]}
        )
        return process_citadel_instance
