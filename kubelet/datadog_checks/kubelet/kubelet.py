# (C) Datadog, Inc. 2016-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import division

import re
import sys
from collections import defaultdict
from copy import deepcopy

import requests
from kubeutil import get_connection_info
from six import iteritems
from six.moves.urllib.parse import urlparse

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheck
from datadog_checks.base.checks.kubelet_base.base import KubeletBase, KubeletCredentials, urljoin
from datadog_checks.base.config import _is_affirmative
from datadog_checks.base.errors import CheckException, SkipInstanceError
from datadog_checks.base.utils.tagging import tagger

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


from .cadvisor import CadvisorScraper
from .common import (
    CADVISOR_DEFAULT_PORT,
    PodListUtils,
    get_container_label,
    get_prometheus_url,
    replace_container_rt_prefix,
    tags_for_docker,
)
from .probes import ProbesPrometheusScraperMixin
from .prometheus import CadvisorPrometheusScraperMixin
from .summary import SummaryScraperMixin

KUBELET_HEALTH_PATH = '/healthz'
NODE_SPEC_PATH = '/spec'
POD_LIST_PATH = '/pods'
CADVISOR_METRICS_PATH = '/metrics/cadvisor'
KUBELET_METRICS_PATH = '/metrics'
STATS_PATH = '/stats/summary/'
PROBES_METRICS_PATH = '/metrics/probes'

# Suffixes per
# https://github.com/kubernetes/kubernetes/blob/8fd414537b5143ab039cb910590237cabf4af783/pkg/api/resource/suffix.go#L108
FACTORS = {
    'n': float(1) / (1000 * 1000 * 1000),
    'u': float(1) / (1000 * 1000),
    'm': float(1) / 1000,
    'k': 1000,
    'M': 1000 * 1000,
    'G': 1000 * 1000 * 1000,
    'T': 1000 * 1000 * 1000 * 1000,
    'P': 1000 * 1000 * 1000 * 1000 * 1000,
    'E': 1000 * 1000 * 1000 * 1000 * 1000 * 1000,
    'Ki': 1024,
    'Mi': 1024 * 1024,
    'Gi': 1024 * 1024 * 1024,
    'Ti': 1024 * 1024 * 1024 * 1024,
    'Pi': 1024 * 1024 * 1024 * 1024 * 1024,
    'Ei': 1024 * 1024 * 1024 * 1024 * 1024 * 1024,
}


WHITELISTED_CONTAINER_STATE_REASONS = {
    'waiting': [
        'errimagepull',
        'imagepullbackoff',
        'crashloopbackoff',
        'containercreating',
        'createcontainererror',
        'invalidimagename',
        'createcontainerconfigerror',
    ],
    'terminated': ['oomkilled', 'containercannotrun', 'error'],
}

DEFAULT_GAUGES = {
    'rest_client_requests_total': 'rest.client.requests',
    'go_threads': 'go_threads',
    'go_goroutines': 'go_goroutines',
    'kubelet_pleg_last_seen_seconds': 'kubelet.pleg.last_seen',
}

DEPRECATED_GAUGES = {
    'kubelet_runtime_operations': 'kubelet.runtime.operations',
    'kubelet_runtime_operations_errors': 'kubelet.runtime.errors',
    'kubelet_docker_operations': 'kubelet.docker.operations',
    'kubelet_docker_operations_errors': 'kubelet.docker.errors',
}

NEW_1_14_GAUGES = {
    'kubelet_runtime_operations_total': 'kubelet.runtime.operations',
    'kubelet_runtime_operations_errors_total': 'kubelet.runtime.errors',
}

DEFAULT_HISTOGRAMS = {
    'apiserver_client_certificate_expiration_seconds': 'apiserver.certificate.expiration',
    'kubelet_pleg_relist_duration_seconds': 'kubelet.pleg.relist_duration',
    'kubelet_pleg_relist_interval_seconds': 'kubelet.pleg.relist_interval',
}

DEFAULT_SUMMARIES = {}

DEPRECATED_SUMMARIES = {
    'kubelet_network_plugin_operations_latency_microseconds': 'kubelet.network_plugin.latency',
    'kubelet_pod_start_latency_microseconds': 'kubelet.pod.start.duration',
    'kubelet_pod_worker_latency_microseconds': 'kubelet.pod.worker.duration',
    'kubelet_pod_worker_start_latency_microseconds': 'kubelet.pod.worker.start.duration',
    'kubelet_runtime_operations_latency_microseconds': 'kubelet.runtime.operations.duration',
    'kubelet_docker_operations_latency_microseconds': 'kubelet.docker.operations.duration',
}

NEW_1_14_SUMMARIES = {}

TRANSFORM_VALUE_HISTOGRAMS = {
    'kubelet_network_plugin_operations_duration_seconds': 'kubelet.network_plugin.latency',
    'kubelet_pod_start_duration_seconds': 'kubelet.pod.start.duration',
    'kubelet_pod_worker_duration_seconds': 'kubelet.pod.worker.duration',
    'kubelet_pod_worker_start_duration_seconds': 'kubelet.pod.worker.start.duration',
    'kubelet_runtime_operations_duration_seconds': 'kubelet.runtime.operations.duration',
}

DEFAULT_MAX_DEPTH = 10
DEFAULT_ENABLED_RATES = ['diskio.io_service_bytes.stats.total', 'network.??_bytes', 'cpu.*.total']
DEFAULT_ENABLED_GAUGES = [
    'memory.cache',
    'memory.usage',
    'memory.swap',
    'memory.working_set',
    'memory.rss',
    'filesystem.usage',
]
DEFAULT_POD_LEVEL_METRICS = ['network.*']


class KubeletCheck(
    CadvisorPrometheusScraperMixin,
    OpenMetricsBaseCheck,
    CadvisorScraper,
    SummaryScraperMixin,
    ProbesPrometheusScraperMixin,
    KubeletBase,
):
    """
    Collect metrics from Kubelet.
    """

    DEFAULT_METRIC_LIMIT = 0

    COUNTER_METRICS = {
        'kubelet_evictions': 'kubelet.evictions',
        'kubelet_pleg_discard_events': 'kubelet.pleg.discard_events',
    }

    VOLUME_METRICS = {
        'kubelet_volume_stats_available_bytes': 'kubelet.volume.stats.available_bytes',
        'kubelet_volume_stats_capacity_bytes': 'kubelet.volume.stats.capacity_bytes',
        'kubelet_volume_stats_used_bytes': 'kubelet.volume.stats.used_bytes',
        'kubelet_volume_stats_inodes': 'kubelet.volume.stats.inodes',
        'kubelet_volume_stats_inodes_free': 'kubelet.volume.stats.inodes_free',
        'kubelet_volume_stats_inodes_used': 'kubelet.volume.stats.inodes_used',
    }

    VOLUME_TAG_KEYS_TO_EXCLUDE = ['persistentvolumeclaim', 'pod_phase']

    def __init__(self, name, init_config, instances):
        if _is_affirmative(datadog_agent.get_config("kubelet_core_check_enabled")):
            raise SkipInstanceError(
                "The kubelet core check is enabled, skipping initialization of the python kubelet check"
            )
        self.KUBELET_METRIC_TRANSFORMERS = {
            'kubelet_container_log_filesystem_used_bytes': self.kubelet_container_log_filesystem_used_bytes,
            'rest_client_request_latency_seconds': self.rest_client_latency,
            'rest_client_request_duration_seconds': self.rest_client_latency,
        }

        self.NAMESPACE = 'kubernetes'
        if instances is not None and len(instances) > 1:
            raise Exception('Kubelet check only supports one configured instance.')
        inst = instances[0] if instances else None

        # configuring the collection of some of the metrics (via the cadvisor or the summary endpoint)
        self.max_depth = inst.get('max_depth', DEFAULT_MAX_DEPTH)
        enabled_gauges = inst.get('enabled_gauges', DEFAULT_ENABLED_GAUGES)
        self.enabled_gauges = ["{0}.{1}".format(self.NAMESPACE, x) for x in enabled_gauges]
        enabled_rates = inst.get('enabled_rates', DEFAULT_ENABLED_RATES)
        self.enabled_rates = ["{0}.{1}".format(self.NAMESPACE, x) for x in enabled_rates]
        pod_level_metrics = inst.get('pod_level_metrics', DEFAULT_POD_LEVEL_METRICS)
        self.pod_level_metrics = ["{0}.{1}".format(self.NAMESPACE, x) for x in pod_level_metrics]

        # configuring the different instances use to scrape the 3 kubelet endpoints
        prom_url, get_prom_url_err = get_prometheus_url("dummy_url/cadvisor")

        cadvisor_instance = self._create_cadvisor_prometheus_instance(inst, prom_url)
        if len(inst.get('ignore_metrics', {})) > 0:
            # Add entries from configuration to ignore_metrics in the cadvisor collector.
            cadvisor_instance['ignore_metrics'].extend(
                m for m in inst.get('ignore_metrics', {}) if m not in cadvisor_instance['ignore_metrics']
            )

        kubelet_instance = self._create_kubelet_prometheus_instance(inst, prom_url)
        probes_instance = self._create_probes_prometheus_instance(inst, prom_url)
        generic_instances = [cadvisor_instance, kubelet_instance, probes_instance]

        super(KubeletCheck, self).__init__(name, init_config, generic_instances)

        # we need to wait that `super()` was executed to have the self.log instance created
        if get_prom_url_err:
            self.log.warning('get_prometheus_url() failed to query the kublet, err: %s', get_prom_url_err)

        self.cadvisor_legacy_port = inst.get('cadvisor_port', CADVISOR_DEFAULT_PORT)
        self.cadvisor_legacy_url = None

        self.use_stats_summary_as_source = inst.get('use_stats_summary_as_source')
        if self.use_stats_summary_as_source is None and sys.platform == 'win32':
            self.use_stats_summary_as_source = True

        self.cadvisor_scraper_config = self.get_scraper_config(cadvisor_instance)
        # Filter out system slices (empty pod name) to reduce memory footprint
        self.cadvisor_scraper_config['_text_filter_blacklist'] = ['pod_name=""', 'pod=""']

        self.kubelet_scraper_config = self.get_scraper_config(kubelet_instance)

        self.probes_scraper_config = self.get_scraper_config(probes_instance)

        counter_transformers = {k: self.send_always_counter for k in self.COUNTER_METRICS}

        histogram_transformers = {
            k: self._histogram_from_seconds_to_microseconds(v) for k, v in TRANSFORM_VALUE_HISTOGRAMS.items()
        }

        volume_metric_transformers = {k: self.append_pod_tags_to_volume_metrics for k in self.VOLUME_METRICS}

        self.transformers = {}
        for d in [
            self.PROBES_METRIC_TRANSFORMERS,
            self.CADVISOR_METRIC_TRANSFORMERS,
            self.KUBELET_METRIC_TRANSFORMERS,
            counter_transformers,
            histogram_transformers,
            volume_metric_transformers,
        ]:
            self.transformers.update(d)

        self.first_run = True

    def _create_kubelet_prometheus_instance(self, instance, prom_url):
        """
        Create a copy of the instance and set default values.
        This is so the base class can create a scraper_config with the proper values.
        """
        kubelet_instance = deepcopy(instance)
        kubelet_instance.update(
            {
                'namespace': self.NAMESPACE,
                'prometheus_url': instance.get('kubelet_metrics_endpoint', urljoin(prom_url, KUBELET_METRICS_PATH)),
                'metrics': [
                    DEFAULT_GAUGES,
                    DEPRECATED_GAUGES,
                    NEW_1_14_GAUGES,
                    DEFAULT_HISTOGRAMS,
                    DEFAULT_SUMMARIES,
                    DEPRECATED_SUMMARIES,
                    NEW_1_14_SUMMARIES,
                ],
                # Defaults that were set when the Kubelet scraper was based on PrometheusScraper
                'send_monotonic_counter': instance.get('send_monotonic_counter', False),
                'health_service_check': instance.get('health_service_check', False),
            }
        )
        return kubelet_instance

    def _create_pod_tags_by_pvc(self, pod_list):
        """
        Return a map, e.g.
            {
                "<kube_namespace>/<persistentvolumeclaim>": [<list_of_pod_tags>],
                "<kube_namespace1>/<persistentvolumeclaim1>": [<list_of_pod_tags1>],
            }
        that can be used to add pod tags to associated volume metrics
        """
        pod_tags_by_pvc = defaultdict(set)
        pods = pod_list.get('items', [])
        for pod in pods:
            # get kubernetes namespace of PVC
            kube_ns = pod.get('metadata', {}).get('namespace')
            if not kube_ns:
                continue

            # get pod id
            pod_id = pod.get('metadata', {}).get('uid')
            if not pod_id:
                self.log.debug('skipping pod with no uid')
                continue

            # get pod name
            pod_name = pod.get('metadata', {}).get('name')
            if not pod_name:
                self.log.debug('skipping pod with no name')
                continue

            # get volumes
            volumes = pod.get('spec', {}).get('volumes')
            if not volumes:
                continue

            # get tags from tagger
            tags = tagger.tag('kubernetes_pod_uid://%s' % pod_id, tagger.ORCHESTRATOR) or None
            if not tags:
                continue

            # remove tags that don't apply to PVCs
            for excluded_tag in self.VOLUME_TAG_KEYS_TO_EXCLUDE:
                tags = [t for t in tags if not t.startswith(excluded_tag + ':')]

            for v in volumes:
                # get PVC
                pvc_name = v.get('persistentVolumeClaim', {}).get('claimName')
                if pvc_name:
                    pod_tags_by_pvc['{}/{}'.format(kube_ns, pvc_name)].update(tags)

                # get standalone PVC associated to potential EVC
                # when a generic ephemeral volume is created, an associated pvc named <pod_name>-<volume_name>
                # is created (https://docs.openshift.com/container-platform/4.11/storage/generic-ephemeral-vols.html).
                evc = v.get('ephemeral', {}).get('volumeClaimTemplate')
                volume_name = v.get('name')
                if evc and volume_name:
                    pod_tags_by_pvc['{}/{}-{}'.format(kube_ns, pod_name, volume_name)].update(tags)

        return pod_tags_by_pvc

    def check(self, instance):
        # Kubelet credential defaults are determined dynamically during every
        # check run so we must make sure that configuration is always reset
        self.reset_http_config()

        kubelet_conn_info = get_connection_info()
        endpoint = kubelet_conn_info.get('url')
        if endpoint is None:
            raise CheckException("Unable to detect the kubelet URL automatically: " + kubelet_conn_info.get('err', ''))

        self._update_kubelet_url_and_bearer_token(instance, endpoint)

        self.kube_health_url = urljoin(endpoint, KUBELET_HEALTH_PATH)
        self.node_spec_url = urljoin(endpoint, NODE_SPEC_PATH)
        self.pod_list_url = urljoin(endpoint, POD_LIST_PATH)
        self.stats_url = urljoin(endpoint, STATS_PATH)
        self.instance_tags = instance.get('tags', [])
        self.kubelet_credentials = KubeletCredentials(kubelet_conn_info)

        # Test the kubelet health ASAP
        self._perform_kubelet_check(self.instance_tags)

        # Kubelet credentials handling
        self.kubelet_credentials.configure_scraper(self.cadvisor_scraper_config)
        self.kubelet_credentials.configure_scraper(self.kubelet_scraper_config)
        self.kubelet_credentials.configure_scraper(self.probes_scraper_config)

        if 'metrics_endpoint' in instance:
            self.log.warning('metrics_endpoint is deprecated, please specify cadvisor_metrics_endpoint instead.')

        http_handler = self.get_http_handler(self.probes_scraper_config)
        probes_metrics_endpoint = urljoin(endpoint, PROBES_METRICS_PATH)
        if not self.detect_probes(http_handler, probes_metrics_endpoint):
            # Disable probe metrics collection (k8s 1.15+ required)
            self.probes_scraper_config['prometheus_url'] = ''

        # Legacy cadvisor support
        try:
            self.cadvisor_legacy_url = self.detect_cadvisor(endpoint, self.cadvisor_legacy_port)
        except Exception as e:
            self.log.debug('cAdvisor not found, running in prometheus mode: %s', e)

        self.pod_list = self.retrieve_pod_list()
        self.pod_list_utils = PodListUtils(self.pod_list)

        self.pod_tags_by_pvc = self._create_pod_tags_by_pvc(self.pod_list)

        self._report_node_metrics(self.instance_tags)
        self._report_pods_running(self.pod_list, self.instance_tags)
        self._report_container_spec_metrics(self.pod_list, self.instance_tags)
        self._report_container_state_metrics(self.pod_list, self.instance_tags)

        self.stats = self._retrieve_stats()
        self.process_stats_summary(
            self.pod_list_utils, self.stats, self.instance_tags, self.use_stats_summary_as_source
        )

        if self.cadvisor_legacy_url:  # Legacy cAdvisor
            self.log.debug('processing legacy cadvisor metrics')
            self.process_cadvisor(instance, self.cadvisor_legacy_url, self.pod_list, self.pod_list_utils)
        elif self.cadvisor_scraper_config['prometheus_url']:  # Prometheus
            self.log.debug('processing cadvisor metrics')
            self.process(self.cadvisor_scraper_config, metric_transformers=self.transformers)

        if self.kubelet_scraper_config['prometheus_url']:  # Prometheus
            self.log.debug('processing kubelet metrics')
            self.process(self.kubelet_scraper_config, metric_transformers=self.transformers)

        if self.probes_scraper_config['prometheus_url']:
            self.log.debug('processing probe metrics')
            self.process(self.probes_scraper_config, metric_transformers=self.transformers)

        self.first_run = False

        # Free up memory
        self.pod_list = None
        self.pod_list_utils = None

    def _retrieve_node_spec(self):
        """
        Retrieve node spec from kubelet.
        """
        node_resp = self.perform_kubelet_query(self.node_spec_url)
        return node_resp

    def _retrieve_stats(self):
        """
        Retrieve stats from kubelet.
        """
        try:
            stats_response = self.perform_kubelet_query(self.stats_url)
            stats_response.raise_for_status()
            return stats_response.json()
        except Exception as e:
            self.log.warning('GET on kubelet s `/stats/summary` failed: %s', e)
            return {}

    def _report_node_metrics(self, instance_tags):
        try:
            node_resp = self._retrieve_node_spec()
            node_resp.raise_for_status()
        except requests.HTTPError as e:
            if node_resp.status_code == 404:
                # ignore HTTPError, for supporting k8s >= 1.18 in a degrated mode
                # in 1.18 the /spec can be reactivated from the kubelet config
                # in 1.19 the /spec will removed.
                return
            raise e
        node_spec = node_resp.json()
        num_cores = node_spec.get('num_cores', 0)
        memory_capacity = node_spec.get('memory_capacity', 0)

        tags = instance_tags
        self.gauge(self.NAMESPACE + '.cpu.capacity', float(num_cores), tags)
        self.gauge(self.NAMESPACE + '.memory.capacity', float(memory_capacity), tags)

    def _perform_kubelet_check(self, instance_tags):
        """Runs local service checks"""
        service_check_base = self.NAMESPACE + '.kubelet.check'
        is_ok = True
        url = self.kube_health_url

        try:
            req = self.perform_kubelet_query(url)
            for line in req.iter_lines(decode_unicode=True):
                # avoid noise; this check is expected to fail since we override the container hostname
                if line.find('hostname') != -1:
                    continue

                matches = re.match(r'\[(.)\]([^\s]+) (.*)?', line)
                if not matches or len(matches.groups()) < 2:
                    continue

                service_check_name = service_check_base + '.' + matches.group(2)
                status = matches.group(1)
                if status == '+':
                    self.service_check(service_check_name, AgentCheck.OK, tags=instance_tags)
                else:
                    self.service_check(service_check_name, AgentCheck.CRITICAL, tags=instance_tags)
                    is_ok = False

        except Exception as e:
            self.log.warning('kubelet check %s failed: %s', url, e)
            self.service_check(
                service_check_base,
                AgentCheck.CRITICAL,
                message='Kubelet check %s failed: %s' % (url, str(e)),
                tags=instance_tags,
            )
        else:
            if is_ok:
                self.service_check(service_check_base, AgentCheck.OK, tags=instance_tags)
            else:
                self.service_check(service_check_base, AgentCheck.CRITICAL, tags=instance_tags)

    def _report_pods_running(self, pods, instance_tags):
        """
        Reports the number of running pods on this node and the running
        containers in pods, tagged by service and creator.

        :param pods: pod list object
        :param instance_tags: list of tags
        """
        pods_tag_counter = defaultdict(int)
        containers_tag_counter = defaultdict(int)
        for pod in pods.get('items', []):
            # Containers reporting
            has_container_running = False
            for field in ['containerStatuses', 'initContainerStatuses']:
                containers = pod.get('status', {}).get(field, [])
                for container in containers:
                    container_id = container.get('containerID')
                    if not container_id:
                        self.log.debug('skipping container with no id')
                        continue
                    if "running" not in container.get('state', {}):
                        continue
                    has_container_running = True
                    tags = tagger.tag(replace_container_rt_prefix(container_id), tagger.LOW) or None
                    if not tags:
                        continue
                    tags += instance_tags
                    hash_tags = tuple(sorted(tags))
                    containers_tag_counter[hash_tags] += 1
            # Pod reporting
            if not has_container_running:
                continue
            pod_id = pod.get('metadata', {}).get('uid')
            if not pod_id:
                self.log.debug('skipping pod with no uid')
                continue
            tags = tagger.tag('kubernetes_pod_uid://%s' % pod_id, tagger.LOW) or None
            if not tags:
                continue
            tags += instance_tags
            hash_tags = tuple(sorted(tags))
            pods_tag_counter[hash_tags] += 1
        for tags, count in iteritems(pods_tag_counter):
            self.gauge(self.NAMESPACE + '.pods.running', count, list(tags))
        for tags, count in iteritems(containers_tag_counter):
            self.gauge(self.NAMESPACE + '.containers.running', count, list(tags))

    def _report_container_spec_metrics(self, pod_list, instance_tags):
        """Reports pod requests & limits by looking at pod specs."""
        for pod in pod_list.get('items', []):
            pod_name = pod.get('metadata', {}).get('name')
            pod_phase = pod.get('status', {}).get('phase')
            if self._should_ignore_pod(pod_name, pod_phase):
                continue

            for status_field, spec_field in [
                ('containerStatuses', 'containers'),
                ('initContainerStatuses', 'initContainers'),
            ]:
                for ctr in pod.get('spec', {}).get(spec_field, []):
                    if not ctr.get('resources'):
                        continue

                    c_name = ctr.get('name', '')
                    cid = None
                    completed = False
                    for ctr_status in pod.get('status', {}).get(status_field, []):
                        if ctr_status.get('name') == c_name:
                            # we found the correct container status, but we don't want to report resources
                            # for completed containers
                            if ctr_status.get('state', {}).get('terminated', {}).get('reason', '') == 'Completed':
                                completed = True
                            # it is already prefixed with 'runtime://'
                            cid = ctr_status.get('containerID')
                            break
                    if not cid or completed:
                        continue

                    pod_uid = pod.get('metadata', {}).get('uid')
                    if self.pod_list_utils.is_excluded(cid, pod_uid):
                        continue

                    tags = tagger.tag(replace_container_rt_prefix(cid), tagger.HIGH)
                    if not tags:
                        continue
                    tags += instance_tags

                    try:
                        for resource, value_str in iteritems(ctr.get('resources', {}).get('requests', {})):
                            value = self.parse_quantity(value_str)
                            self.gauge('{}.{}.requests'.format(self.NAMESPACE, resource), value, tags)
                    except (KeyError, AttributeError) as e:
                        self.log.debug("Unable to retrieve container requests for %s: %s", c_name, e)

                    try:
                        for resource, value_str in iteritems(ctr.get('resources', {}).get('limits', {})):
                            value = self.parse_quantity(value_str)
                            self.gauge('{}.{}.limits'.format(self.NAMESPACE, resource), value, tags)
                    except (KeyError, AttributeError) as e:
                        self.log.debug("Unable to retrieve container limits for %s: %s", c_name, e)

    def _report_container_state_metrics(self, pod_list, instance_tags):
        """Reports container state & reasons by looking at container statuses"""
        if pod_list.get('expired_count'):
            self.gauge(self.NAMESPACE + '.pods.expired', pod_list.get('expired_count'), tags=instance_tags)

        for pod in pod_list.get('items', []):
            pod_name = pod.get('metadata', {}).get('name')
            pod_uid = pod.get('metadata', {}).get('uid')

            if not pod_name or not pod_uid:
                continue

            for field in ['containerStatuses', 'initContainerStatuses']:
                for ctr_status in pod.get('status', {}).get(field, []):
                    c_name = ctr_status.get('name')
                    cid = ctr_status.get('containerID')

                    if not c_name or not cid:
                        continue

                    if self.pod_list_utils.is_excluded(cid, pod_uid):
                        continue

                    tags = tagger.tag(replace_container_rt_prefix(cid), tagger.ORCHESTRATOR)
                    if not tags:
                        continue
                    tags += instance_tags

                    restart_count = ctr_status.get('restartCount', 0)
                    self.gauge(self.NAMESPACE + '.containers.restarts', restart_count, tags)

                    for metric_name, field_name in [('state', 'state'), ('last_state', 'lastState')]:
                        c_state = ctr_status.get(field_name, {})

                        for state_name in ['terminated', 'waiting']:
                            state_reasons = WHITELISTED_CONTAINER_STATE_REASONS.get(state_name, [])
                            self._submit_container_state_metric(metric_name, state_name, c_state, state_reasons, tags)

    def _submit_container_state_metric(self, metric_name, state_name, c_state, state_reasons, tags):
        reason_tags = []

        state_value = c_state.get(state_name)
        if state_value:
            reason = state_value.get('reason', '')

            if reason.lower() in state_reasons:
                reason_tags.append('reason:%s' % (reason))
            else:
                return

            gauge_name = '{}.containers.{}.{}'.format(self.NAMESPACE, metric_name, state_name)
            self.gauge(gauge_name, 1, tags + reason_tags)

    def _update_kubelet_url_and_bearer_token(self, instance, endpoint):
        if 'cadvisor_metrics_endpoint' in instance:
            cadvisor_metrics_endpoint = instance.get(
                'cadvisor_metrics_endpoint', urljoin(endpoint, CADVISOR_METRICS_PATH)
            )
        else:
            cadvisor_metrics_endpoint = instance.get('metrics_endpoint', urljoin(endpoint, CADVISOR_METRICS_PATH))

        self.update_prometheus_url(instance, self.cadvisor_scraper_config, cadvisor_metrics_endpoint)

        kubelet_metrics_endpoint = instance.get('kubelet_metrics_endpoint', urljoin(endpoint, KUBELET_METRICS_PATH))
        self.update_prometheus_url(instance, self.kubelet_scraper_config, kubelet_metrics_endpoint)

        probes_metrics_endpoint = urljoin(endpoint, PROBES_METRICS_PATH)
        instance_probes_metrics_endpoint = instance.get('probes_metrics_endpoint', probes_metrics_endpoint)
        self.update_prometheus_url(instance, self.probes_scraper_config, instance_probes_metrics_endpoint)

    @staticmethod
    def parse_quantity(string):
        """
        Parse quantity allows to convert the value in the resources spec like:
        resources:
          requests:
            cpu: "100m"
            memory": "200Mi"
          limits:
            memory: "300Mi"
        :param string: str
        :return: float
        """
        # If the string has an exponent, Python converts it automatically with `float`
        # A quantity can't have both an exponent and a unit suffix
        # Quantities must match the regular expression '^([+-]?[0-9.]+)([eEinumkKMGTP]*[-+]?[0-9]*)$'
        # Ref: https://github.com/kubernetes/apimachinery/blob/d82afe1e363acae0e8c0953b1bc230d65fdb50e2/pkg/api/resource/quantity.go#L144-L148
        try:
            converted_value = float(string)
            return converted_value
        # The string can't directly be handled by `float` : it has a suffix to parse
        except ValueError:
            number, unit = '', ''
            for char in string:
                if char.isdigit() or char == '.':
                    number += char
                else:
                    unit += char
            return float(number) * FACTORS.get(unit, 1)

    @staticmethod
    def _should_ignore_pod(name, phase):
        """
        Pods that are neither pending or running should not be counted
        in resource requests and limits.
        """
        if not name or phase not in ["Running", "Pending"]:
            return True
        return False

    def send_always_counter(self, metric, scraper_config, hostname=None):
        metric_name_with_namespace = '{}.{}'.format(scraper_config['namespace'], self.COUNTER_METRICS[metric.name])
        for sample in metric.samples:
            val = sample[self.SAMPLE_VALUE]
            if not self._is_value_valid(val):
                self.log.debug("Metric value is not supported for metric %s", sample[self.SAMPLE_NAME])
                continue
            custom_hostname = self._get_hostname(hostname, sample, scraper_config)
            # Determine the tags to send
            tags = self._metric_tags(metric.name, val, sample, scraper_config, hostname=custom_hostname)
            self.monotonic_count(
                metric_name_with_namespace,
                val,
                tags=tags,
                hostname=custom_hostname,
                flush_first_value=not self.first_run,
            )

    def append_pod_tags_to_volume_metrics(self, metric, scraper_config, hostname=None):
        metric_name_with_namespace = '{}.{}'.format(scraper_config['namespace'], self.VOLUME_METRICS[metric.name])
        for sample in metric.samples:
            val = sample[self.SAMPLE_VALUE]
            if not self._is_value_valid(val):
                self.log.debug("Metric value is not supported for metric %s", sample[self.SAMPLE_NAME])
                continue
            custom_hostname = self._get_hostname(hostname, sample, scraper_config)
            # Determine the tags to send
            tags = self._metric_tags(metric.name, val, sample, scraper_config, hostname=custom_hostname)
            pvc_name, kube_ns = None, None
            for label_name, label_value in iteritems(sample[self.SAMPLE_LABELS]):
                if label_name == "persistentvolumeclaim":
                    pvc_name = label_value
                elif label_name == "namespace":
                    kube_ns = label_value
                if pvc_name and kube_ns:
                    break

            if self.pod_list_utils.is_namespace_excluded(kube_ns):
                continue

            pod_tags = self.pod_tags_by_pvc.get('{}/{}'.format(kube_ns, pvc_name), {})
            tags.extend(pod_tags)
            self.gauge(metric_name_with_namespace, val, tags=list(set(tags)), hostname=custom_hostname)

    def kubelet_container_log_filesystem_used_bytes(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.kubelet.container.log_filesystem.used_bytes'
        for sample in metric.samples:
            self._filter_and_send_gauge_sample(metric_name, sample)

    def _filter_and_send_gauge_sample(self, metric_name, sample):
        labels = sample[OpenMetricsBaseCheck.SAMPLE_LABELS]
        container_id = self.pod_list_utils.get_cid_by_labels(labels)
        tags = []
        if container_id is not None:
            if self.pod_list_utils.is_excluded(container_id):
                return

            tags = tags_for_docker(replace_container_rt_prefix(container_id), tagger.HIGH, True)
            if not tags:
                self.log.debug(
                    "Tags not found for container: %s/%s/%s:%s",
                    get_container_label(labels, 'namespace'),
                    get_container_label(labels, 'pod'),
                    get_container_label(labels, 'container'),
                    container_id,
                )

        self.gauge(metric_name, sample[self.SAMPLE_VALUE], tags + self.instance_tags)

    def rest_client_latency(self, metric, scraper_config):
        for sample in metric.samples:
            try:
                sample.labels['url'] = self._sanitize_url_label(sample.labels['url'])
            except KeyError:
                pass
        return self.submit_openmetric("rest.client.latency", metric, scraper_config)

    @staticmethod
    def _sanitize_url_label(url):
        u = urlparse(url)
        return u.path
