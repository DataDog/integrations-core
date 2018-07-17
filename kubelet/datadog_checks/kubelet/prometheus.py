# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# project
from datadog_checks.checks.prometheus import PrometheusScraper
from tagger import get_tags

# check
from .common import is_static_pending_pod, get_pod_by_uid

METRIC_TYPES = ['counter', 'gauge', 'summary']
# container-specific metrics should have all these labels
CONTAINER_LABELS = ['container_name', 'namespace', 'pod_name', 'name', 'image', 'id']


class CadvisorPrometheusScraper(PrometheusScraper):
    """
    This class scrapes metrics for the kubelet "/metrics/cadvisor" prometheus endpoint and submits
    them on behalf of a check.
    """

    def __init__(self, check):
        super(CadvisorPrometheusScraper, self).__init__(check)

        self.NAMESPACE = 'kubernetes'
        self.instance_tags = []

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

    @staticmethod
    def _is_container_metric(labels):
        """
        Return whether a metric is about a container or not.
        It can be about pods, or even higher levels in the cgroup hierarchy
        and we don't want to report on that.
        :param metric:
        :return: bool
        """
        for lbl in CONTAINER_LABELS:
            if lbl == 'container_name':
                for ml in labels:
                    if ml.name == lbl:
                        if ml.value == '' or ml.value == 'POD':
                            return False
            if lbl not in [ml.name for ml in labels]:
                return False
        return True

    @staticmethod
    def _is_pod_metric(labels):
        """
        Return whether a metric is about a pod or not.
        It can be about containers, pods, or higher levels in the cgroup hierarchy
        and we don't want to report on that.
        :param metric
        :return bool
        """
        for ml in labels:
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
        container_id = CadvisorPrometheusScraper._get_container_label(labels, "id")
        if container_id:
            return container_id.split('/')[-1]

    @staticmethod
    def _get_container_id_if_container_metric(labels):
        """
        Checks the labels indicate a container metric,
        then extract the container id from them.
        :param labels
        :return str or None
        """
        if CadvisorPrometheusScraper._is_container_metric(labels):
            return CadvisorPrometheusScraper._get_container_id(labels)

    @staticmethod
    def _get_pod_uid(labels):
        """
        Return the id of a pod
        :param labels:
        :return: str or None
        """
        pod_id = CadvisorPrometheusScraper._get_container_label(labels, "id")
        if pod_id:
            for part in pod_id.split('/'):
                if part.startswith('pod'):
                    return part[3:]

    @staticmethod
    def _get_pod_uid_if_pod_metric(labels):
        """
        Checks the labels indicate a pod metric,
        then extract the pod uid from them.
        :param labels
        :return str or None
        """
        if CadvisorPrometheusScraper._is_pod_metric(labels):
            return CadvisorPrometheusScraper._get_pod_uid(labels)

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
        return get_pod_by_uid(pod_uid, self.pod_list)

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
        container_name = CadvisorPrometheusScraper._get_container_label(labels, "container_name")
        if container_name:
            return ["kube_container_name:%s" % container_name]
        return []

    def process(self, endpoint, **kwargs):
        self.pod_list = kwargs.get('pod_list')
        self.container_filter = kwargs.get('container_filter')

        instance = kwargs.get('instance')
        if instance:
            self.instance_tags = instance.get('tags', [])

        super(CadvisorPrometheusScraper, self).process(endpoint, **kwargs)

        # Free up memory
        self.pod_list = None
        self.container_filter = None

    @staticmethod
    def _sum_values_by_context(message, uid_from_labels):
        """
        Iterates over all metrics in a message and sums the values
        matching the same uid. Modifies the metric family in place.
        :param message: prometheus metric family
        :param uid_from_labels: function mapping a metric.label to a unique context id
        :return: dict with uid as keys, metric object references as values
        """
        seen = {}
        metric_type = METRIC_TYPES[message.type]
        for metric in message.metric:
            uid = uid_from_labels(metric.label)
            if not uid:
                metric.Clear()  # Ignore this metric message
                continue
            # Sum the counter value accross all cores
            if uid not in seen:
                seen[uid] = metric
            else:
                getattr(seen[uid], metric_type).value += getattr(metric, metric_type).value
                metric.Clear()  # Ignore this metric message

        return seen

    def _process_container_rate(self, metric_name, message):
        """
        Takes a simple metric about a container, reports it as a rate.
        If several series are found for a given container, values are summed before submission.
        """
        if message.type >= len(METRIC_TYPES):
            self.log.error("Metric type %s unsupported for metric %s" % (message.type, message.name))
            return

        metrics = self._sum_values_by_context(message, self._get_container_id_if_container_metric)
        for c_id, metric in metrics.iteritems():
            pod_uid = self._get_pod_uid(metric.label)
            if self.container_filter.is_excluded(c_id, pod_uid):
                continue

            tags = get_tags('docker://%s' % c_id, True)
            tags += self.instance_tags

            # FIXME we are forced to do that because the Kubelet PodList isn't updated
            # for static pods, see https://github.com/kubernetes/kubernetes/pull/59948
            pod = self._get_pod_by_metric_label(metric.label)
            if pod is not None and is_static_pending_pod(pod):
                tags += get_tags('kubernetes_pod://%s' % pod["metadata"]["uid"], True)
                tags += self._get_kube_container_name(metric.label)
                tags = list(set(tags))

            val = getattr(metric, METRIC_TYPES[message.type]).value

            self.check.rate(metric_name, val, tags)

    def _process_pod_rate(self, metric_name, message):
        """
        Takes a simple metric about a pod, reports it as a rate.
        If several series are found for a given pod, values are summed before submission.
        """
        if message.type >= len(METRIC_TYPES):
            self.log.error("Metric type %s unsupported for metric %s" % (message.type, message.name))
            return

        metrics = self._sum_values_by_context(message, self._get_pod_uid_if_pod_metric)
        for pod_uid, metric in metrics.iteritems():
            if '.network.' in metric_name and self._is_pod_host_networked(pod_uid):
                continue
            tags = get_tags('kubernetes_pod://%s' % pod_uid, True)
            tags += self.instance_tags
            val = getattr(metric, METRIC_TYPES[message.type]).value
            self.check.rate(metric_name, val, tags)

    def _process_usage_metric(self, m_name, message, cache):
        """
        Takes a metrics message, a metric name, and a cache dict where it will store
        container_name --> (value, tags) so that _process_limit_metric can compute usage_pct
        it also submit said value and tags as a gauge.
        """
        # track containers that still exist in the cache
        seen_keys = {k: False for k in cache}

        metrics = self._sum_values_by_context(message, self._get_container_id_if_container_metric)
        for c_id, metric in metrics.iteritems():
            c_name = self._get_container_label(metric.label, 'name')
            if not c_name:
                continue
            pod_uid = self._get_pod_uid(metric.label)
            if self.container_filter.is_excluded(c_id, pod_uid):
                continue

            tags = get_tags('docker://%s' % c_id, True)
            tags += self.instance_tags

            # FIXME we are forced to do that because the Kubelet PodList isn't updated
            # for static pods, see https://github.com/kubernetes/kubernetes/pull/59948
            pod = self._get_pod_by_metric_label(metric.label)
            if pod is not None and is_static_pending_pod(pod):
                tags += get_tags('kubernetes_pod://%s' % pod["metadata"]["uid"], True)
                tags += self._get_kube_container_name(metric.label)
                tags = list(set(tags))

            val = getattr(metric, METRIC_TYPES[message.type]).value
            cache[c_name] = (val, tags)
            seen_keys[c_name] = True
            self.check.gauge(m_name, val, tags)

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
        metrics = self._sum_values_by_context(message, self._get_container_id_if_container_metric)
        for c_id, metric in metrics.iteritems():
            limit = getattr(metric, METRIC_TYPES[message.type]).value
            pod_uid = self._get_pod_uid(metric.label)
            if self.container_filter.is_excluded(c_id, pod_uid):
                continue

            tags = get_tags('docker://%s' % c_id, True)
            tags += self.instance_tags

            if m_name:
                self.check.gauge(m_name, limit, tags)

            if pct_m_name and limit > 0:
                c_name = self._get_container_label(metric.label, 'name')
                if not c_name:
                    continue
                usage, tags = cache.get(c_name, (None, None))
                if usage:
                    self.check.gauge(pct_m_name, float(usage / float(limit)), tags)
                else:
                    self.log.debug("No corresponding usage found for metric %s and "
                                   "container %s, skipping usage_pct for now." % (pct_m_name, c_name))

    def container_cpu_usage_seconds_total(self, message, **_):
        metric_name = self.NAMESPACE + '.cpu.usage.total'
        for metric in message.metric:
            # Convert cores in nano cores
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
