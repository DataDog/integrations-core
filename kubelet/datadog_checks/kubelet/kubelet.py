# (C) Datadog, Inc. 2016-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import logging
import re
from collections import defaultdict
from urlparse import urljoin
from copy import deepcopy

# 3p
import requests

# project
from datadog_checks.checks import AgentCheck
from datadog_checks.checks.openmetrics import OpenMetricsBaseCheck
from datadog_checks.errors import CheckException
from kubeutil import get_connection_info
from tagger import get_tags

# check
from .common import CADVISOR_DEFAULT_PORT, PodListUtils, KubeletCredentials
from .cadvisor import CadvisorScraper
from .prometheus import CadvisorPrometheusScraperMixin

KUBELET_HEALTH_PATH = '/healthz'
NODE_SPEC_PATH = '/spec'
POD_LIST_PATH = '/pods'
CADVISOR_METRICS_PATH = '/metrics/cadvisor'
KUBELET_METRICS_PATH = '/metrics'

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

log = logging.getLogger('collector')


class KubeletCheck(CadvisorPrometheusScraperMixin, OpenMetricsBaseCheck, CadvisorScraper):
    """
    Collect metrics from Kubelet.
    """
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, agentConfig, instances=None):
        self.NAMESPACE = 'kubernetes'
        if instances is not None and len(instances) > 1:
            raise Exception('Kubelet check only supports one configured instance.')
        inst = instances[0] if instances else None

        cadvisor_instance = self._create_cadvisor_prometheus_instance(inst)
        kubelet_instance = self._create_kubelet_prometheus_instance(inst)
        generic_instances = [cadvisor_instance, kubelet_instance]
        super(KubeletCheck, self).__init__(name, init_config, agentConfig, generic_instances)

        self.cadvisor_legacy_port = inst.get('cadvisor_port', CADVISOR_DEFAULT_PORT)
        self.cadvisor_legacy_url = None

        self.cadvisor_scraper_config = self.get_scraper_config(cadvisor_instance)
        # Filter out system slices (empty pod name) to reduce memory footprint
        self.cadvisor_scraper_config['_text_filter_blacklist'] = ['pod_name=""']

        self.kubelet_scraper_config = self.get_scraper_config(kubelet_instance)

    def _create_kubelet_prometheus_instance(self, instance):
        """
        Create a copy of the instance and set default values.
        This is so the base class can create a scraper_config with the proper values.
        """
        kubelet_instance = deepcopy(instance)
        kubelet_instance.update({
            'namespace': self.NAMESPACE,

            # We need to specify a prometheus_url so the base class can use it as the key for our config_map,
            # we specify a dummy url that will be replaced in the `check()` function. We append it with "kubelet"
            # so the key is different than the cadvisor scraper.
            'prometheus_url': instance.get('kubelet_metrics_endpoint', 'dummy_url/kubelet'),
            'metrics': [{
                'apiserver_client_certificate_expiration_seconds': 'apiserver.certificate.expiration',
                'rest_client_requests_total': 'rest.client.requests',
                'rest_client_request_latency_seconds': 'rest.client.latency',
                'kubelet_runtime_operations': 'kubelet.runtime.operations',
                'kubelet_runtime_operations_errors': 'kubelet.runtime.errors',
                'kubelet_network_plugin_operations_latency_microseconds': 'kubelet.network_plugin.latency',
            }],
            # Defaults that were set when the Kubelet scraper was based on PrometheusScraper
            'send_monotonic_counter': instance.get('send_monotonic_counter', False),
            'health_service_check': instance.get('health_service_check', False)
        })
        return kubelet_instance

    def check(self, instance):
        kubelet_conn_info = get_connection_info()
        endpoint = kubelet_conn_info.get('url')
        if endpoint is None:
            raise CheckException("Unable to detect the kubelet URL automatically.")

        if 'cadvisor_metrics_endpoint' in instance:
            self.cadvisor_scraper_config['prometheus_url'] = \
                instance.get('cadvisor_metrics_endpoint', urljoin(endpoint, CADVISOR_METRICS_PATH))
        else:
            self.cadvisor_scraper_config['prometheus_url'] = instance.get('metrics_endpoint',
                                                                          urljoin(endpoint, CADVISOR_METRICS_PATH))

        if 'metrics_endpoint' in instance:
            self.log.warning('metrics_endpoint is deprecated, please specify cadvisor_metrics_endpoint instead.')

        self.kubelet_scraper_config['prometheus_url'] = instance.get('kubelet_metrics_endpoint',
                                                                     urljoin(endpoint, KUBELET_METRICS_PATH))

        self.kube_health_url = urljoin(endpoint, KUBELET_HEALTH_PATH)
        self.node_spec_url = urljoin(endpoint, NODE_SPEC_PATH)
        self.pod_list_url = urljoin(endpoint, POD_LIST_PATH)

        # Kubelet credentials handling
        self.kubelet_credentials = KubeletCredentials(kubelet_conn_info)
        self.kubelet_credentials.configure_scraper(
            self.cadvisor_scraper_config
        )
        self.kubelet_credentials.configure_scraper(
            self.kubelet_scraper_config
        )

        # Legacy cadvisor support
        try:
            self.cadvisor_legacy_url = self.detect_cadvisor(endpoint, self.cadvisor_legacy_port)
        except Exception as e:
            self.log.debug('cAdvisor not found, running in prometheus mode: %s' % str(e))

        self.pod_list = self.retrieve_pod_list()
        self.pod_list_utils = PodListUtils(self.pod_list)

        self.instance_tags = instance.get('tags', [])
        self._perform_kubelet_check(self.instance_tags)
        self._report_node_metrics(self.instance_tags)
        self._report_pods_running(self.pod_list, self.instance_tags)
        self._report_container_spec_metrics(self.pod_list, self.instance_tags)

        if self.cadvisor_legacy_url:  # Legacy cAdvisor
            self.log.debug('processing legacy cadvisor metrics')
            self.process_cadvisor(
                instance,
                self.cadvisor_legacy_url,
                self.pod_list,
                self.pod_list_utils
            )
        elif self.cadvisor_scraper_config['prometheus_url']:  # Prometheus
            self.log.debug('processing cadvisor metrics')
            self.process(
                self.cadvisor_scraper_config,
                metric_transformers=self.CADVISOR_METRIC_TRANSFORMERS
            )

        if self.kubelet_scraper_config['prometheus_url']:  # Prometheus
            self.log.debug('processing kubelet metrics')
            self.process(
                self.kubelet_scraper_config
            )

        # Free up memory
        self.pod_list = None
        self.pod_list_utils = None

    def perform_kubelet_query(self, url, verbose=True, timeout=10):
        """
        Perform and return a GET request against kubelet. Support auth and TLS validation.
        """
        return requests.get(
            url,
            timeout=timeout,
            verify=self.kubelet_credentials.verify(),
            cert=self.kubelet_credentials.cert_pair(),
            headers=self.kubelet_credentials.headers(url),
            params={'verbose': verbose}
        )

    def retrieve_pod_list(self):
        try:
            pod_list = self.perform_kubelet_query(self.pod_list_url).json()
            if pod_list.get("items") is None:
                # Sanitize input: if no pod are running, 'items' is a NoneObject
                pod_list['items'] = []
            return pod_list
        except Exception as e:
            self.log.debug('failed to retrieve pod list from the kubelet at %s : %s'
                           % (self.pod_list_url, str(e)))
            return None

    def _retrieve_node_spec(self):
        """
        Retrieve node spec from kubelet.
        """
        node_spec = self.perform_kubelet_query(self.node_spec_url).json()
        # TODO: report allocatable for cpu, mem, and pod capacity
        # if we can get it locally or thru the DCA instead of the /nodes endpoint directly
        return node_spec

    def _report_node_metrics(self, instance_tags):
        node_spec = self._retrieve_node_spec()
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
            for line in req.iter_lines():
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
            self.log.warning('kubelet check %s failed: %s' % (url, str(e)))
            self.service_check(service_check_base, AgentCheck.CRITICAL,
                               message='Kubelet check %s failed: %s' % (url, str(e)), tags=instance_tags)
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
            # Pod reporting
            pod_id = pod.get('metadata', {}).get('uid')
            if not pod_id:
                self.log.debug('skipping pod with no uid')
                continue
            tags = get_tags('kubernetes_pod://%s' % pod_id, False) or None
            if not tags:
                continue
            tags += instance_tags
            hash_tags = tuple(sorted(tags))
            pods_tag_counter[hash_tags] += 1
            # Containers reporting
            containers = pod.get('status', {}).get('containerStatuses', [])
            for container in containers:
                container_id = container.get('containerID')
                if not container_id:
                    self.log.debug('skipping container with no id')
                    continue
                tags = get_tags(container_id, False) or None
                if not tags:
                    continue
                tags += instance_tags
                hash_tags = tuple(sorted(tags))
                containers_tag_counter[hash_tags] += 1
        for tags, count in pods_tag_counter.iteritems():
            self.gauge(self.NAMESPACE + '.pods.running', count, list(tags))
        for tags, count in containers_tag_counter.iteritems():
            self.gauge(self.NAMESPACE + '.containers.running', count, list(tags))

    def _report_container_spec_metrics(self, pod_list, instance_tags):
        """Reports pod requests & limits by looking at pod specs."""
        for pod in pod_list['items']:
            pod_name = pod.get('metadata', {}).get('name')
            if not pod_name:
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

                tags = get_tags('%s' % cid, True) + instance_tags

                try:
                    for resource, value_str in ctr.get('resources', {}).get('requests', {}).iteritems():
                        value = self.parse_quantity(value_str)
                        self.gauge('{}.{}.requests'.format(self.NAMESPACE, resource), value, tags)
                except (KeyError, AttributeError) as e:
                    self.log.debug("Unable to retrieve container requests for %s: %s", c_name, e)

                try:
                    for resource, value_str in ctr.get('resources', {}).get('limits', {}).iteritems():
                        value = self.parse_quantity(value_str)
                        self.gauge('{}.{}.limits'.format(self.NAMESPACE, resource), value, tags)
                except (KeyError, AttributeError) as e:
                    self.log.debug("Unable to retrieve container limits for %s: %s", c_name, e)

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
