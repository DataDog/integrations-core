# (C) Datadog, Inc. 2016-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import division

import json
import logging
import re
import sys
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta

import requests
from kubeutil import get_connection_info
from six import iteritems
from urllib3.exceptions import InsecureRequestWarning

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheck
from datadog_checks.base.errors import CheckException
from datadog_checks.base.utils.date import UTC, parse_rfc3339
from datadog_checks.base.utils.tagging import tagger
from datadog_checks.base.utils.warnings_util import disable_warnings_ctx

from .cadvisor import CadvisorScraper
from .common import CADVISOR_DEFAULT_PORT, KubeletCredentials, PodListUtils, replace_container_rt_prefix, urljoin
from .prometheus import CadvisorPrometheusScraperMixin
from .summary import SummaryScraperMixin

try:
    from datadog_agent import get_config
except ImportError:

    def get_config(key):
        return ""


KUBELET_HEALTH_PATH = '/healthz'
NODE_SPEC_PATH = '/spec'
POD_LIST_PATH = '/pods'
CADVISOR_METRICS_PATH = '/metrics/cadvisor'
KUBELET_METRICS_PATH = '/metrics'
STATS_PATH = '/stats/summary/'

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
    'waiting': ['errimagepull', 'imagepullbackoff', 'crashloopbackoff', 'containercreating'],
    'terminated': ['oomkilled', 'containercannotrun', 'error'],
}

DEFAULT_GAUGES = {
    'rest_client_requests_total': 'rest.client.requests',
}

DEPRECATED_GAUGES = {
    'kubelet_runtime_operations': 'kubelet.runtime.operations',
    'kubelet_runtime_operations_errors': 'kubelet.runtime.errors',
}

NEW_1_14_GAUGES = {
    'kubelet_runtime_operations_total': 'kubelet.runtime.operations',
    'kubelet_runtime_operations_errors_total': 'kubelet.runtime.errors',
    'kubelet_container_log_filesystem_used_bytes': 'kubelet.container.log_filesystem.used_bytes',
}

DEFAULT_HISTOGRAMS = {
    'apiserver_client_certificate_expiration_seconds': 'apiserver.certificate.expiration',
}

DEPRECATED_HISTOGRAMS = {
    'rest_client_request_latency_seconds': 'rest.client.latency',
}

NEW_1_14_HISTOGRAMS = {
    'rest_client_request_duration_seconds': 'rest.client.latency',
}

DEFAULT_SUMMARIES = {}

DEPRECATED_SUMMARIES = {
    'kubelet_network_plugin_operations_latency_microseconds': 'kubelet.network_plugin.latency',
}

NEW_1_14_SUMMARIES = {}

TRANSFORM_VALUE_HISTOGRAMS = {
    'kubelet_network_plugin_operations_duration_seconds': 'kubelet.network_plugin.latency',
}

log = logging.getLogger('collector')


class ExpiredPodFilter(object):
    """
    Allows to filter old pods out of the podlist by providing a decoding hook
    """

    def __init__(self, cutoff_date):
        self.expired_count = 0
        self.cutoff_date = cutoff_date

    def json_hook(self, obj):
        # Not a pod (hook is called for all objects)
        if 'metadata' not in obj or 'status' not in obj:
            return obj

        # Quick exit for running/pending containers
        pod_phase = obj.get('status', {}).get('phase')
        if pod_phase in ["Running", "Pending"]:
            return obj

        # Filter out expired terminated pods, based on container finishedAt time
        expired = True
        for ctr in obj['status'].get('containerStatuses', []):
            if "terminated" not in ctr.get("state", {}):
                expired = False
                break
            finishedTime = ctr["state"]["terminated"].get("finishedAt")
            if not finishedTime:
                expired = False
                break
            if parse_rfc3339(finishedTime) > self.cutoff_date:
                expired = False
                break
        if not expired:
            return obj

        # We are ignoring this pod
        self.expired_count += 1
        return None


class KubeletCheck(CadvisorPrometheusScraperMixin, OpenMetricsBaseCheck, CadvisorScraper, SummaryScraperMixin):
    """
    Collect metrics from Kubelet.
    """

    DEFAULT_METRIC_LIMIT = 0

    COUNTER_METRICS = {'kubelet_evictions': 'kubelet.evictions'}

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
        self.NAMESPACE = 'kubernetes'
        if instances is not None and len(instances) > 1:
            raise Exception('Kubelet check only supports one configured instance.')
        inst = instances[0] if instances else None

        cadvisor_instance = self._create_cadvisor_prometheus_instance(inst)
        kubelet_instance = self._create_kubelet_prometheus_instance(inst)
        generic_instances = [cadvisor_instance, kubelet_instance]
        super(KubeletCheck, self).__init__(name, init_config, generic_instances)

        self.cadvisor_legacy_port = inst.get('cadvisor_port', CADVISOR_DEFAULT_PORT)
        self.cadvisor_legacy_url = None

        self.use_stats_summary_as_source = inst.get('use_stats_summary_as_source')
        if self.use_stats_summary_as_source is None and sys.platform == 'win32':
            self.use_stats_summary_as_source = True

        self.cadvisor_scraper_config = self.get_scraper_config(cadvisor_instance)
        # Filter out system slices (empty pod name) to reduce memory footprint
        self.cadvisor_scraper_config['_text_filter_blacklist'] = ['pod_name=""', 'pod=""']

        self.kubelet_scraper_config = self.get_scraper_config(kubelet_instance)

        counter_transformers = {k: self.send_always_counter for k in self.COUNTER_METRICS}

        histogram_transformers = {
            k: self._histogram_from_seconds_to_microseconds(v) for k, v in TRANSFORM_VALUE_HISTOGRAMS.items()
        }

        volume_metric_transformers = {k: self.append_pod_tags_to_volume_metrics for k in self.VOLUME_METRICS}

        self.transformers = {}
        for d in [
            self.CADVISOR_METRIC_TRANSFORMERS,
            counter_transformers,
            histogram_transformers,
            volume_metric_transformers,
        ]:
            self.transformers.update(d)

    def _create_kubelet_prometheus_instance(self, instance):
        """
        Create a copy of the instance and set default values.
        This is so the base class can create a scraper_config with the proper values.
        """
        kubelet_instance = deepcopy(instance)
        kubelet_instance.update(
            {
                'namespace': self.NAMESPACE,
                # We need to specify a prometheus_url so the base class can use it as the key for our config_map,
                # we specify a dummy url that will be replaced in the `check()` function. We append it with "kubelet"
                # so the key is different than the cadvisor scraper.
                'prometheus_url': instance.get('kubelet_metrics_endpoint', 'dummy_url/kubelet'),
                'metrics': [
                    DEFAULT_GAUGES,
                    DEPRECATED_GAUGES,
                    NEW_1_14_GAUGES,
                    DEFAULT_HISTOGRAMS,
                    DEPRECATED_HISTOGRAMS,
                    NEW_1_14_HISTOGRAMS,
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

    def _create_pod_tags_by_pvc(self, pods):
        """
        Return a map, e.g.
            {
                "<kube_namespace>/<persistentvolumeclaim>": [<list_of_pod_tags>],
                "<kube_namespace1>/<persistentvolumeclaim1>": [<list_of_pod_tags1>],
            }
        that can be used to add pod tags to associated volume metrics
        """
        pod_tags_by_pvc = defaultdict(set)
        for pod in pods['items']:
            # get kubernetes namespace of PVC
            kube_ns = pod.get('metadata', {}).get('namespace')
            if not kube_ns:
                continue

            # get volumes
            volumes = pod.get('spec', {}).get('volumes')
            if not volumes:
                continue

            # get pod id
            pod_id = pod.get('metadata', {}).get('uid')
            if not pod_id:
                self.log.debug('skipping pod with no uid')
                continue

            # get tags from tagger
            tags = tagger.tag('kubernetes_pod_uid://%s' % pod_id, tagger.ORCHESTRATOR) or None
            if not tags:
                continue

            # remove tags that don't apply to PVCs
            for excluded_tag in self.VOLUME_TAG_KEYS_TO_EXCLUDE:
                tags = [t for t in tags if not t.startswith(excluded_tag + ':')]

            # get PVC
            for v in volumes:
                pvc_name = v.get('persistentVolumeClaim', {}).get('claimName')
                if pvc_name:
                    pod_tags_by_pvc['{}/{}'.format(kube_ns, pvc_name)].update(tags)

        return pod_tags_by_pvc

    def check(self, instance):
        # Kubelet credential defaults are determined dynamically during every
        # check run so we must make sure that configuration is always reset
        self.reset_http_config()

        kubelet_conn_info = get_connection_info()
        endpoint = kubelet_conn_info.get('url')
        if endpoint is None:
            raise CheckException("Unable to detect the kubelet URL automatically.")

        self.kube_health_url = urljoin(endpoint, KUBELET_HEALTH_PATH)
        self.node_spec_url = urljoin(endpoint, NODE_SPEC_PATH)
        self.pod_list_url = urljoin(endpoint, POD_LIST_PATH)
        self.stats_url = urljoin(endpoint, STATS_PATH)
        self.instance_tags = instance.get('tags', [])
        self.kubelet_credentials = KubeletCredentials(kubelet_conn_info)

        # Test the kubelet health ASAP
        self._perform_kubelet_check(self.instance_tags)

        if 'cadvisor_metrics_endpoint' in instance:
            self.cadvisor_scraper_config['prometheus_url'] = instance.get(
                'cadvisor_metrics_endpoint', urljoin(endpoint, CADVISOR_METRICS_PATH)
            )
        else:
            self.cadvisor_scraper_config['prometheus_url'] = instance.get(
                'metrics_endpoint', urljoin(endpoint, CADVISOR_METRICS_PATH)
            )

        if 'metrics_endpoint' in instance:
            self.log.warning('metrics_endpoint is deprecated, please specify cadvisor_metrics_endpoint instead.')

        self.kubelet_scraper_config['prometheus_url'] = instance.get(
            'kubelet_metrics_endpoint', urljoin(endpoint, KUBELET_METRICS_PATH)
        )

        # Kubelet credentials handling
        self.kubelet_credentials.configure_scraper(self.cadvisor_scraper_config)
        self.kubelet_credentials.configure_scraper(self.kubelet_scraper_config)

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

        # Free up memory
        self.pod_list = None
        self.pod_list_utils = None

    def perform_kubelet_query(self, url, verbose=True, timeout=10, stream=False):
        """
        Perform and return a GET request against kubelet. Support auth and TLS validation.
        """
        with disable_warnings_ctx(InsecureRequestWarning, disable=not self.kubelet_credentials.verify()):
            return requests.get(
                url,
                timeout=timeout,
                verify=self.kubelet_credentials.verify(),
                cert=self.kubelet_credentials.cert_pair(),
                headers=self.kubelet_credentials.headers(url),
                params={'verbose': verbose},
                stream=stream,
            )

    def retrieve_pod_list(self):
        try:
            cutoff_date = self._compute_pod_expiration_datetime()
            with self.perform_kubelet_query(self.pod_list_url, stream=True) as r:
                if cutoff_date:
                    f = ExpiredPodFilter(cutoff_date)
                    pod_list = json.load(r.raw, object_hook=f.json_hook)
                    pod_list['expired_count'] = f.expired_count
                    if pod_list.get("items") is not None:
                        # Filter out None items from the list
                        pod_list['items'] = [p for p in pod_list['items'] if p is not None]
                else:
                    pod_list = json.load(r.raw)

            if pod_list.get("items") is None:
                # Sanitize input: if no pod are running, 'items' is a NoneObject
                pod_list['items'] = []
            return pod_list
        except Exception as e:
            self.log.warning('failed to retrieve pod list from the kubelet at %s : %s', self.pod_list_url, e)
            return None

    @staticmethod
    def _compute_pod_expiration_datetime():
        """
        Looks up the agent's kubernetes_pod_expiration_duration option and returns either:
          - None if expiration is disabled (set to 0)
          - A (timezone aware) datetime object to compare against
        """
        try:
            seconds = int(get_config("kubernetes_pod_expiration_duration"))
            if seconds == 0:  # Expiration disabled
                return None
            return datetime.utcnow().replace(tzinfo=UTC) - timedelta(seconds=seconds)
        except (ValueError, TypeError):
            return None

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
        for pod in pods['items']:
            # Containers reporting
            containers = pod.get('status', {}).get('containerStatuses', [])
            has_container_running = False
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
        for pod in pod_list['items']:
            pod_name = pod.get('metadata', {}).get('name')
            pod_phase = pod.get('status', {}).get('phase')
            if self._should_ignore_pod(pod_name, pod_phase):
                continue

            for ctr in pod['spec']['containers']:
                if not ctr.get('resources'):
                    continue

                c_name = ctr.get('name', '')
                cid = None
                for ctr_status in pod['status'].get('containerStatuses', []):
                    if ctr_status.get('name') == c_name:
                        # it is already prefixed with 'runtime://'
                        cid = ctr_status.get('containerID')
                        break
                if not cid:
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

        for pod in pod_list['items']:
            pod_name = pod.get('metadata', {}).get('name')
            pod_uid = pod.get('metadata', {}).get('uid')

            if not pod_name or not pod_uid:
                continue

            for ctr_status in pod['status'].get('containerStatuses', []):
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

                for (metric_name, field_name) in [('state', 'state'), ('last_state', 'lastState')]:
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
            self.monotonic_count(metric_name_with_namespace, val, tags=tags, hostname=custom_hostname)

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

            pod_tags = self.pod_tags_by_pvc.get('{}/{}'.format(kube_ns, pvc_name), {})
            tags.extend(pod_tags)
            self.gauge(metric_name_with_namespace, val, tags=list(set(tags)), hostname=custom_hostname)
