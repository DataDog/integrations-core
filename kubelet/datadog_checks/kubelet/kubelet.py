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
from datadog_checks.checks.prometheus import PrometheusCheck
from kubeutil import get_connection_info
from tagger import get_tags

METRIC_TYPES = ['counter', 'gauge', 'summary']
# container-specific metrics should have all these labels
CONTAINER_LABELS = ['container_name', 'namespace', 'pod_name', 'name', 'image', 'id']

KUBELET_HEALTH_PATH = '/healthz'
NODE_SPEC_PATH = '/spec'
POD_LIST_PATH = '/pods/'
CADVISOR_METRICS_PATH = '/metrics/cadvisor'

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


class KubeletCheck(PrometheusCheck):
    """
    Collect container metrics from Kubelet.
    """

    def __init__(self, name, init_config, agentConfig, instances=None):
        super(KubeletCheck, self).__init__(name, init_config, agentConfig, instances)
        self.NAMESPACE = 'kubernetes'

        if instances is not None and len(instances) > 1:
            raise Exception('Kubelet check only supports one configured instance.')
        inst = instances[0] if instances else None

        self.kube_node_labels = inst.get('node_labels_to_host_tags', {})
        self.metrics_mapper = {
            'kubelet_runtime_operations_errors': 'kubelet.runtime.errors',
        }
        self.ignore_metrics = [
            'container_cpu_cfs_periods_total',
            'container_cpu_cfs_throttled_periods_total',
            'container_cpu_cfs_throttled_seconds_total',
            'container_cpu_load_average_10s',
            'container_cpu_system_seconds_total',
            'container_cpu_user_seconds_total',
            'container_fs_inodes_free',
            'container_fs_inodes_total',
            'container_fs_io_current',
            'container_fs_io_time_seconds_total',
            'container_fs_io_time_weighted_seconds_total',
            'container_fs_read_seconds_total',
            'container_fs_reads_merged_total',
            'container_fs_reads_total',
            'container_fs_sector_reads_total',
            'container_fs_sector_writes_total',
            'container_fs_write_seconds_total',
            'container_fs_writes_merged_total',
            'container_fs_writes_total',
            'container_last_seen',
            'container_start_time_seconds',
            'container_spec_memory_swap_limit_bytes',
            'container_scrape_error'
        ]

        # these are filled by container_<metric-name>_usage_<metric-unit>
        # and container_<metric-name>_limit_<metric-unit> reads it to compute <metric-name>usage_pct
        self.fs_usage_bytes = {}
        self.mem_usage_bytes = {}

    def check(self, instance):
        self.kubelet_conn_info = get_connection_info()
        endpoint = self.kubelet_conn_info.get('url')
        if endpoint is None:
            raise CheckException("Unable to find metrics_endpoint in config "
                                 "file or detect the kubelet URL automatically.")

        self.metrics_url = instance.get('metrics_endpoint') or urljoin(endpoint, CADVISOR_METRICS_PATH)
        self.kube_health_url = urljoin(endpoint, KUBELET_HEALTH_PATH)
        self.node_spec_url = urljoin(endpoint, NODE_SPEC_PATH)
        self.pod_list_url = urljoin(endpoint, POD_LIST_PATH)

        # By default we send the buckets.
        send_buckets = instance.get('send_histograms_buckets', True)
        if send_buckets is not None and str(send_buckets).lower() == 'false':
            send_buckets = False
        else:
            send_buckets = True

        try:
            self.pod_list = self.retrieve_pod_list()
        except Exception:
            self.pod_list = None

        instance_tags = instance.get('tags', [])
        self._perform_kubelet_check(instance_tags)
        self._report_node_metrics(instance_tags)
        self._report_pods_running(self.pod_list, instance_tags)
        self._report_container_spec_metrics(self.pod_list, instance_tags)
        self.process(self.metrics_url, send_histograms_buckets=send_buckets, instance=instance)

    def perform_kubelet_query(self, url, verbose=True, timeout=10):
        """
        Perform and return a GET request against kubelet. Support auth and TLS validation.
        """
        headers = None
        cert = (self.kubelet_conn_info.get('client_crt'), self.kubelet_conn_info.get('client_key'))
        if not cert[0] or not cert[1]:
            cert = None
        else:
            self.ssl_cert = cert  # prometheus check setting

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

    @staticmethod
    def _is_container_metric(metric):
        """
        Return whether a metric is about a container or not.
        It can be about pods, or even higher levels in the cgroup hierarchy
        and we don't want to report on that.
        :param metric:
        :return: bool
        """
        for lbl in CONTAINER_LABELS:
            if lbl == 'container_name':
                for ml in metric.label:
                    if ml.name == lbl:
                        if ml.value == '' or ml.value == 'POD':
                            return False
            if lbl not in [ml.name for ml in metric.label]:
                return False
        return True

    @staticmethod
    def _is_pod_metric(metric):
        """
        Return whether a metric is about a pod or not.
        It can be about containers, pods, or higher levels in the cgroup hierarchy
        and we don't want to report on that.
        :param metric
        :return bool
        """
        for ml in metric.label:
            if ml.name == 'container_name' and ml.value == 'POD':
                return True
            # container_cpu_usage_seconds_total has an id label that is a cgroup path
            # eg: /kubepods/burstable/pod531c80d9-9fc4-11e7-ba8b-42010af002bb
            # FIXME: this was needed because of a bug:
            # https://github.com/kubernetes/kubernetes/pull/51473
            # starting from k8s 1.8 we can remove this
            elif ml.name == 'id' and ml.value.split('/')[-1].startswith('pod'):
                return True
        return False

    @staticmethod
    def _get_container_label(labels, l_name):
        """
        Iter on all labels to find the label.name equal to the l_name
        :param labels: list of labels
        :param l_name: str
        :return: str or None
        """
        for label in labels:
            if label.name == l_name:
                return label.value

    @staticmethod
    def _get_container_id(labels):
        """
        Should only be called on a container-scoped metric
        as it doesn't do any validation of the container id.
        It simply returns the last part of the cgroup hierarchy.
        :param labels
        :return str or None
        """
        container_id = KubeletCheck._get_container_label(labels, "id")
        if container_id:
            return container_id.split('/')[-1]

    @staticmethod
    def _get_pod_uid(labels):
        """
        Return the id of a pod
        :param labels:
        :return: str or None
        """
        pod_id = KubeletCheck._get_container_label(labels, "id")
        if pod_id:
            for part in pod_id.split('/'):
                if part.startswith('pod'):
                    return part[3:]

    def _is_pod_host_networked(self, pod_uid):
        """
        Return if the pod is on host Network
        Return False if the Pod isn't in the pod list
        :param pod_uid: str
        :return: bool
        """
        for pod in self.pod_list['items']:
            if pod.get('metadata', {}).get('uid', '') == pod_uid:
                return pod.get('spec', {}).get('hostNetwork', False)
        return False

    def _get_pod_by_metric_label(self, labels):
        """
        :param labels: metric labels: iterable
        :return:
        """
        pod_uid = self._get_pod_uid(labels)
        for pod in self.pod_list["items"]:
            try:
                if pod["metadata"]["uid"] == pod_uid:
                    return pod
            except KeyError:
                continue

        return None

    @staticmethod
    def _is_static_pending_pod(pod):
        """
        Return if the pod is a static pending pod
        See https://github.com/kubernetes/kubernetes/pull/57106
        :param pod: dict
        :return: bool
        """
        try:
            if pod["metadata"]["annotations"]["kubernetes.io/config.source"] == "api":
                return False

            pod_status = pod["status"]
            if pod_status["phase"] != "Pending":
                return False

            return "containerStatuses" not in pod_status
        except KeyError:
            return False

    @staticmethod
    def _get_kube_container_name(labels):
        """
        Get extra tags from metric labels
        label {
          name: "container_name"
          value: "kube-proxy"
        }
        :param labels: metric labels: iterable
        :return: list
        """
        container_name = KubeletCheck._get_container_label(labels, "container_name")
        if container_name:
            return ["kube_container_name:%s" % container_name]
        return []

    def _process_container_rate(self, metric_name, message):
        """Takes a simple metric about a container, reports it as a rate."""
        if message.type >= len(METRIC_TYPES):
            self.log.error("Metric type %s unsupported for metric %s" % (message.type, message.name))
            return

        for metric in message.metric:
            if self._is_container_metric(metric):
                c_id = self._get_container_id(metric.label)
                tags = get_tags('docker://%s' % c_id, True)

                # FIXME we are forced to do that because the Kubelet PodList isn't updated
                # for static pods, see https://github.com/kubernetes/kubernetes/pull/59948
                pod = self._get_pod_by_metric_label(metric.label)
                if pod is not None and self._is_static_pending_pod(pod):
                    tags += get_tags('kubernetes_pod://%s' % pod["metadata"]["uid"], True)
                    tags += self._get_kube_container_name(metric.label)
                    tags = list(set(tags))

                val = getattr(metric, METRIC_TYPES[message.type]).value
                self.rate(metric_name, val, tags)

    def _process_pod_rate(self, metric_name, message):
        """Takes a simple metric about a pod, reports it as a rate."""
        if message.type >= len(METRIC_TYPES):
            self.log.error("Metric type %s unsupported for metric %s" % (message.type, message.name))
            return

        for metric in message.metric:
            if self._is_pod_metric(metric):
                pod_uid = self._get_pod_uid(metric.label)
                if '.network.' in metric_name and self._is_pod_host_networked(pod_uid):
                    continue
                tags = get_tags('kubernetes_pod://%s' % pod_uid, True)
                val = getattr(metric, METRIC_TYPES[message.type]).value
                self.rate(metric_name, val, tags)

    def _process_usage_metric(self, m_name, message, cache):
        """
        Takes a metrics message, a metric name, and a cache dict where it will store
        container_name --> (value, tags) so that _process_limit_metric can compute usage_pct
        it also submit said value and tags as a gauge.
        """
        # track containers that still exist in the cache
        seen_keys = {k: False for k in cache}
        for metric in message.metric:
            if self._is_container_metric(metric):
                c_id = self._get_container_id(metric.label)
                c_name = self._get_container_label(metric.label, 'name')
                if not c_name:
                    continue
                tags = get_tags('docker://%s' % c_id, True)

                # FIXME we are forced to do that because the Kubelet PodList isn't updated
                # for static pods, see https://github.com/kubernetes/kubernetes/pull/59948
                pod = self._get_pod_by_metric_label(metric.label)
                if pod is not None and self._is_static_pending_pod(pod):
                    tags += get_tags('kubernetes_pod://%s' % pod["metadata"]["uid"], True)
                    tags += self._get_kube_container_name(metric.label)
                    tags = list(set(tags))

                val = getattr(metric, METRIC_TYPES[message.type]).value
                cache[c_name] = (val, tags)
                seen_keys[c_name] = True
                self.gauge(m_name, val, tags)

        # purge the cache
        for k, seen in seen_keys.iteritems():
            if not seen:
                del cache[k]

    def _process_limit_metric(self, m_name, message, cache, pct_m_name=None):
        """
        Reports limit metrics if m_name is not an empty string,
        and optionally checks in the given cache if there's a usage
        for each metric in the message and reports the usage_pct
        """
        for metric in message.metric:
            if self._is_container_metric(metric):
                limit = getattr(metric, METRIC_TYPES[message.type]).value
                c_id = self._get_container_id(metric.label)
                tags = get_tags('docker://%s' % c_id, True)

                if m_name:
                    self.gauge(m_name, limit, tags)

                if pct_m_name and limit > 0:
                    c_name = self._get_container_label(metric.label, 'name')
                    if not c_name:
                        continue
                    usage, tags = cache.get(c_name, (None, None))
                    if usage:
                        self.gauge(pct_m_name, float(usage / float(limit)), tags)
                    else:
                        self.log.debug("No corresponding usage found for metric %s and "
                                       "container %s, skipping usage_pct for now." % (pct_m_name, c_name))

    def container_cpu_usage_seconds_total(self, message, **_):
        metric_name = self.NAMESPACE + '.cpu.usage.total'
        for metric in message.metric:
            # convert cores in nano cores
            metric.counter.value *= 10. ** 9

        self._process_container_rate(metric_name, message)

    def container_fs_reads_bytes_total(self, message, **_):
        metric_name = self.NAMESPACE + '.io.read_bytes'
        self._process_container_rate(metric_name, message)

    def container_fs_writes_bytes_total(self, message, **_):
        metric_name = self.NAMESPACE + '.io.write_bytes'
        self._process_container_rate(metric_name, message)

    def container_network_receive_bytes_total(self, message, **_):
        metric_name = self.NAMESPACE + '.network.rx_bytes'
        self._process_pod_rate(metric_name, message)

    def container_network_transmit_bytes_total(self, message, **_):
        metric_name = self.NAMESPACE + '.network.tx_bytes'
        self._process_pod_rate(metric_name, message)

    def container_network_receive_errors_total(self, message, **_):
        metric_name = self.NAMESPACE + '.network.rx_errors'
        self._process_pod_rate(metric_name, message)

    def container_network_transmit_errors_total(self, message, **_):
        metric_name = self.NAMESPACE + '.network.tx_errors'
        self._process_pod_rate(metric_name, message)

    def container_network_transmit_packets_dropped_total(self, message, **_):
        metric_name = self.NAMESPACE + '.network.tx_dropped'
        self._process_pod_rate(metric_name, message)

    def container_network_receive_packets_dropped_total(self, message, **_):
        metric_name = self.NAMESPACE + '.network.rx_dropped'
        self._process_pod_rate(metric_name, message)

    def container_fs_usage_bytes(self, message, **_):
        """
        Number of bytes that are consumed by the container on this filesystem.
        """
        metric_name = self.NAMESPACE + '.filesystem.usage'
        if message.type >= len(METRIC_TYPES):
            self.log.error("Metric type %s unsupported for metric %s" % (message.type, message.name))
            return
        self._process_usage_metric(metric_name, message, self.fs_usage_bytes)

    def container_fs_limit_bytes(self, message, **_):
        """
        Number of bytes that can be consumed by the container on this filesystem.
        This method is used by container_fs_usage_bytes, it doesn't report any metric
        """
        pct_m_name = self.NAMESPACE + '.filesystem.usage_pct'
        if message.type >= len(METRIC_TYPES):
            self.log.error("Metric type %s unsupported for metric %s" % (message.type, message.name))
            return
        self._process_limit_metric('', message, self.fs_usage_bytes, pct_m_name)

    def container_memory_usage_bytes(self, message, **_):
        """TODO: add swap, cache, failcnt and rss"""
        metric_name = self.NAMESPACE + '.memory.usage'
        if message.type >= len(METRIC_TYPES):
            self.log.error("Metric type %s unsupported for metric %s" % (message.type, message.name))
            return
        self._process_usage_metric(metric_name, message, self.mem_usage_bytes)

    def container_spec_memory_limit_bytes(self, message, **_):
        metric_name = self.NAMESPACE + '.memory.limits'
        pct_m_name = self.NAMESPACE + '.memory.usage_pct'
        if message.type >= len(METRIC_TYPES):
            self.log.error("Metric type %s unsupported for metric %s" % (message.type, message.name))
            return
        self._process_limit_metric(metric_name, message, self.mem_usage_bytes, pct_m_name)
