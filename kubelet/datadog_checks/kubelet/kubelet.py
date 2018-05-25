# (C) Datadog, Inc. 2016-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import logging
import re
from urlparse import urljoin

# 3p
import requests

# project
from datadog_checks.checks import AgentCheck
from datadog_checks.errors import CheckException
from datadog_checks.checks.prometheus import PrometheusScraper
from kubeutil import get_connection_info
from tagger import get_tags

# check
from .common import CADVISOR_DEFAULT_PORT, ContainerFilter
from .cadvisor import CadvisorScraper
from .prometheus import CadvisorPrometheusScraper

KUBELET_HEALTH_PATH = '/healthz'
NODE_SPEC_PATH = '/spec'
POD_LIST_PATH = '/pods/'
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


class KubeletCheck(AgentCheck, CadvisorScraper):
    """
    Collect metrics from Kubelet.
    """

    def __init__(self, name, init_config, agentConfig, instances=None):
        super(KubeletCheck, self).__init__(name, init_config, agentConfig, instances)

        self.NAMESPACE = 'kubernetes'

        if instances is not None and len(instances) > 1:
            raise Exception('Kubelet check only supports one configured instance.')
        inst = instances[0] if instances else None

        self.cadvisor_legacy_port = inst.get('cadvisor_port', CADVISOR_DEFAULT_PORT)
        self.cadvisor_legacy_url = None

        self.cadvisor_scraper = CadvisorPrometheusScraper(self)

        self.kubelet_scraper = PrometheusScraper(self)
        self.kubelet_scraper.NAMESPACE = 'kubernetes'
        self.kubelet_scraper.metrics_mapper = {
            'apiserver_client_certificate_expiration_seconds': 'apiserver.certificate.expiration',
            'rest_client_requests_total': 'rest.client.requests',
            'kubelet_runtime_operations': 'kubelet.runtime.operations',
            'kubelet_runtime_operations_errors': 'kubelet.runtime.errors',
        }

    def check(self, instance):
        self.kubelet_conn_info = get_connection_info()
        endpoint = self.kubelet_conn_info.get('url')
        if endpoint is None:
            raise CheckException("Unable to detect the kubelet URL automatically.")

        if 'cadvisor_metrics_endpoint' in instance:
            self.cadvisor_metrics_url = \
                instance.get('cadvisor_metrics_endpoint', urljoin(endpoint, CADVISOR_METRICS_PATH))
        else:
            self.cadvisor_metrics_url = instance.get('metrics_endpoint', urljoin(endpoint, CADVISOR_METRICS_PATH))

        if 'metrics_endpoint' in instance:
            self.log.warning('metrics_endpoint is deprecated, please specify cadvisor_metrics_endpoint instead.')

        self.kubelet_metrics_url = instance.get('kubelet_metrics_endpoint', urljoin(endpoint, KUBELET_METRICS_PATH))

        self.kube_health_url = urljoin(endpoint, KUBELET_HEALTH_PATH)
        self.node_spec_url = urljoin(endpoint, NODE_SPEC_PATH)
        self.pod_list_url = urljoin(endpoint, POD_LIST_PATH)

        # Legacy cadvisor support
        try:
            self.cadvisor_legacy_url = self.detect_cadvisor(endpoint, self.cadvisor_legacy_port)
        except Exception as e:
            self.log.debug('cAdvisor not found, running in prometheus mode: %s' % str(e))

        # By default we send the buckets.
        send_buckets = instance.get('send_histograms_buckets', True)
        if send_buckets is not None and str(send_buckets).lower() == 'false':
            send_buckets = False
        else:
            send_buckets = True

        try:
            self.pod_list = self.retrieve_pod_list()
            if self.pod_list.get("items") is None:
                # Sanitize input: if no pod are running, 'items' is a NoneObject
                self.pod_list['items'] = []
        except Exception:
            self.pod_list = None

        self.container_filter = ContainerFilter(self.pod_list)

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
                self.container_filter
            )
        elif self.cadvisor_metrics_url:  # Prometheus
            self.log.debug('processing cadvisor metrics')
            self.cadvisor_scraper.process(
                self.cadvisor_metrics_url,
                send_histograms_buckets=send_buckets,
                instance=instance,
                pod_list=self.pod_list,
                container_filter=self.container_filter
            )

        if self.kubelet_metrics_url:  # Prometheus
            self.log.debug('processing kubelet metrics')
            self.kubelet_scraper.process(
                self.kubelet_metrics_url,
                send_histograms_buckets=send_buckets,
                instance=instance,
                ignore_unmapped=True
            )

        # Free up memory
        self.pod_list = None
        self.container_filter = None

    def perform_kubelet_query(self, url, verbose=True, timeout=10):
        """
        Perform and return a GET request against kubelet. Support auth and TLS validation.
        """
        headers = None
        cert = (self.kubelet_conn_info.get('client_crt'), self.kubelet_conn_info.get('client_key'))
        if not cert[0] or not cert[1]:
            cert = None
        else:
            # prometheus check settings
            self.ssl_cert = cert[0]
            self.ssl_private_key = cert[1]

        if self.kubelet_conn_info.get('verify_tls') == 'false':
            verify = False
        else:
            verify = self.kubelet_conn_info.get('ca_cert')
        self.ssl_ca_cert = verify  # prometheus check setting

        # if cert-based auth is enabled, don't use the token.
        if not cert and url.lower().startswith('https') and 'token' in self.kubelet_conn_info:
            headers = {'Authorization': 'Bearer {}'.format(self.kubelet_conn_info['token'])}
            self.extra_headers = headers  # prometheus check setting

        return requests.get(url, timeout=timeout, verify=verify,
                            cert=cert, headers=headers, params={'verbose': verbose})

    def retrieve_pod_list(self):
        return self.perform_kubelet_query(self.pod_list_url).json()

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
        Reports the number of running pods on this node
        tagged by service and creator.

        :param pods: pod list object
        :param instance_tags: list of tags
        """
        tag_counter = {}
        for pod in pods['items']:
            pod_id = pod.get('metadata', {}).get('uid')
            tags = get_tags('kubernetes_pod://%s' % pod_id, False) or None
            if not tags:
                continue
            tags += instance_tags
            hash_tags = tuple(sorted(tags))
            if hash_tags in tag_counter.keys():
                tag_counter[hash_tags] += 1
            else:
                tag_counter[hash_tags] = 1
        for tags, count in tag_counter.iteritems():
            self.gauge(self.NAMESPACE + '.pods.running', count, list(tags))

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
                        # it is already prefixed with 'docker://'
                        cid = ctr_status.get('containerID')
                        break
                if not cid:
                    continue

                pod_uid = pod.get('metadata', {}).get('uid')
                if self.container_filter.is_excluded(cid, pod_uid):
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
