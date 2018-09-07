# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# project
from copy import deepcopy
from datadog_checks.checks.openmetrics import OpenMetricsBaseCheck
from tagger import get_tags

# check
from .common import is_static_pending_pod, get_pod_by_uid

METRIC_TYPES = ['counter', 'gauge', 'summary']

# container-specific metrics should have all these labels
CONTAINER_LABELS = ['container_name', 'namespace', 'pod_name', 'name', 'image', 'id']


class CadvisorPrometheusScraperMixin(object):
    """
    This class scrapes metrics for the kubelet "/metrics/cadvisor" prometheus endpoint and submits
    them on behalf of a check.
    """

    def __init__(self, *args, **kwargs):
        super(CadvisorPrometheusScraperMixin, self).__init__(*args, **kwargs)

        # List of strings to filter the input text payload on. If any line contains
        # one of these strings, it will be filtered out before being parsed.
        # INTERNAL FEATURE, might be removed in future versions
        self._text_filter_blacklist = ['container_name=""']

        # these are filled by container_<metric-name>_usage_<metric-unit>
        # and container_<metric-name>_limit_<metric-unit> reads it to compute <metric-name>usage_pct
        self.fs_usage_bytes = {}
        self.mem_usage_bytes = {}

        self.CADVISOR_METRIC_TRANSFORMERS = {
            'container_cpu_usage_seconds_total': self.container_cpu_usage_seconds_total,
            'container_fs_reads_bytes_total': self.container_fs_reads_bytes_total,
            'container_fs_writes_bytes_total': self.container_fs_writes_bytes_total,
            'container_network_receive_bytes_total': self.container_network_receive_bytes_total,
            'container_network_transmit_bytes_total': self.container_network_transmit_bytes_total,
            'container_network_receive_errors_total': self.container_network_receive_errors_total,
            'container_network_transmit_errors_total': self.container_network_transmit_errors_total,
            'container_network_transmit_packets_dropped_total': self.container_network_transmit_packets_dropped_total,
            'container_network_receive_packets_dropped_total': self.container_network_receive_packets_dropped_total,
            'container_fs_usage_bytes': self.container_fs_usage_bytes,
            'container_fs_limit_bytes': self.container_fs_limit_bytes,
            'container_memory_usage_bytes': self.container_memory_usage_bytes,
            'container_spec_memory_limit_bytes': self.container_spec_memory_limit_bytes
        }

    def _create_cadvisor_prometheus_instance(self, instance):
        """
        Create a copy of the instance and set default values.
        This is so the base class can create a scraper_config with the proper values.
        """
        cadvisor_instance = deepcopy(instance)
        cadvisor_instance.update({
            'namespace': self.NAMESPACE,

            # We need to specify a prometheus_url so the base class can use it as the key for our config_map,
            # we specify a dummy url that will be replaced in the `check()` function. We append it with "cadvisor"
            # so the key is different than the kubelet scraper.
            'prometheus_url': instance.get('cadvisor_metrics_endpoint', 'dummy_url/cadvisor'),
            'ignore_metrics': [
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
            ],
            # Defaults that were set when CadvisorPrometheusScraper was based on PrometheusScraper
            'send_monotonic_counter': instance.get('send_monotonic_counter', False),
            'health_service_check': instance.get('health_service_check', False)
        })
        return cadvisor_instance

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
                if lbl in labels:
                    if labels[lbl] == '' or labels[lbl] == 'POD':
                            return False
            if lbl not in labels:
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
        if 'container_name' in labels:
            if labels['container_name'] == 'POD':
                return True
        # container_cpu_usage_seconds_total has an id label that is a cgroup path
        # eg: /kubepods/burstable/pod531c80d9-9fc4-11e7-ba8b-42010af002bb
        # FIXME: this was needed because of a bug:
        # https://github.com/kubernetes/kubernetes/pull/51473
        # starting from k8s 1.8 we can remove this
        if 'id' in labels:
            if labels['id'].split('/')[-1].startswith('pod'):
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
        if l_name in labels:
            return labels[l_name]

    def _get_container_id(self, labels):
        """
        Should only be called on a container-scoped metric
        It gets the container id from the podlist using the metrics labels

        :param labels
        :return str or None
        """
        namespace = CadvisorPrometheusScraperMixin._get_container_label(labels, "namespace")
        pod_name = CadvisorPrometheusScraperMixin._get_container_label(labels, "pod_name")
        container_name = CadvisorPrometheusScraperMixin._get_container_label(labels, "container_name")
        return self.pod_list_utils.get_cid_by_name_tuple((namespace, pod_name, container_name))

    def _get_container_id_if_container_metric(self, labels):
        """
        Checks the labels indicate a container metric,
        then extract the container id from them.

        :param labels
        :return str or None
        """
        if CadvisorPrometheusScraperMixin._is_container_metric(labels):
            return self._get_container_id(labels)

    def _get_pod_uid(self, labels):
        """
        Return the id of a pod
        :param labels:
        :return: str or None
        """
        namespace = CadvisorPrometheusScraperMixin._get_container_label(labels, "namespace")
        pod_name = CadvisorPrometheusScraperMixin._get_container_label(labels, "pod_name")
        return self.pod_list_utils.get_uid_by_name_tuple((namespace, pod_name))

    def _get_pod_uid_if_pod_metric(self, labels):
        """
        Checks the labels indicate a pod metric,
        then extract the pod uid from them.
        :param labels
        :return str or None
        """
        if CadvisorPrometheusScraperMixin._is_pod_metric(labels):
            return self._get_pod_uid(labels)

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
        container_name = CadvisorPrometheusScraperMixin._get_container_label(labels, "container_name")
        if container_name:
            return ["kube_container_name:%s" % container_name]
        return []

    @staticmethod
    def _sum_values_by_context(metric, uid_from_labels):
        """
        Iterates over all metrics in a metric and sums the values
        matching the same uid. Modifies the metric family in place.
        :param metric: prometheus metric family
        :param uid_from_labels: function mapping a metric.label to a unique context id
        :return: dict with uid as keys, metric object references as values
        """
        seen = {}
        for sample in metric.samples:
            uid = uid_from_labels(sample[OpenMetricsBaseCheck.SAMPLE_LABELS])
            if not uid:
                # TODO
                # metric.Clear()  # Ignore this metric message
                continue
            # Sum the counter value accross all contexts
            if uid not in seen:
                seen[uid] = sample
            else:
                # We have to create a new tuple
                seen[uid] = (
                    seen[uid][OpenMetricsBaseCheck.SAMPLE_NAME],
                    seen[uid][OpenMetricsBaseCheck.SAMPLE_LABELS],
                    seen[uid][OpenMetricsBaseCheck.SAMPLE_VALUE] + sample[OpenMetricsBaseCheck.SAMPLE_VALUE]
                )
                # TODO
                # metric.Clear()  # Ignore this metric message

        return seen

    def _process_container_rate(self, metric_name, metric, scraper_config):
        """
        Takes a simple metric about a container, reports it as a rate.
        If several series are found for a given container, values are summed before submission.
        """
        if metric.type not in METRIC_TYPES:
            self.log.error("Metric type %s unsupported for metric %s" % (metric.type, metric.name))
            return

        samples = self._sum_values_by_context(metric, self._get_container_id_if_container_metric)
        for c_id, sample in samples.iteritems():
            pod_uid = self._get_pod_uid(sample[self.SAMPLE_LABELS])
            if self.pod_list_utils.is_excluded(c_id, pod_uid):
                continue

            tags = get_tags(c_id, True)
            tags += scraper_config['custom_tags']

            # FIXME we are forced to do that because the Kubelet PodList isn't updated
            # for static pods, see https://github.com/kubernetes/kubernetes/pull/59948
            pod = self._get_pod_by_metric_label(sample[self.SAMPLE_LABELS])
            if pod is not None and is_static_pending_pod(pod):
                tags += get_tags('kubernetes_pod://%s' % pod["metadata"]["uid"], True)
                tags += self._get_kube_container_name(sample[self.SAMPLE_LABELS])
                tags = list(set(tags))

            val = sample[self.SAMPLE_VALUE]

            self.rate(metric_name, val, tags)

    def _process_pod_rate(self, metric_name, metric, scraper_config):
        """
        Takes a simple metric about a pod, reports it as a rate.
        If several series are found for a given pod, values are summed before submission.
        """
        if metric.type not in METRIC_TYPES:
            self.log.error("Metric type %s unsupported for metric %s" % (metric.type, metric.name))
            return

        samples = self._sum_values_by_context(metric, self._get_pod_uid_if_pod_metric)
        for pod_uid, sample in samples.iteritems():
            if '.network.' in metric_name and self._is_pod_host_networked(pod_uid):
                continue
            tags = get_tags('kubernetes_pod://%s' % pod_uid, True)
            tags += scraper_config['custom_tags']
            val = sample[self.SAMPLE_VALUE]
            self.rate(metric_name, val, tags)

    def _process_usage_metric(self, m_name, metric, cache, scraper_config):
        """
        Takes a metric object, a metric name, and a cache dict where it will store
        container_name --> (value, tags) so that _process_limit_metric can compute usage_pct
        it also submit said value and tags as a gauge.
        """
        # track containers that still exist in the cache
        seen_keys = {k: False for k in cache}

        samples = self._sum_values_by_context(metric, self._get_container_id_if_container_metric)
        for c_id, sample in samples.iteritems():
            c_name = self._get_container_label(sample[self.SAMPLE_LABELS], 'name')
            if not c_name:
                continue
            pod_uid = self._get_pod_uid(sample[self.SAMPLE_LABELS])
            if self.pod_list_utils.is_excluded(c_id, pod_uid):
                continue

            tags = get_tags(c_id, True)
            tags += scraper_config['custom_tags']

            # FIXME we are forced to do that because the Kubelet PodList isn't updated
            # for static pods, see https://github.com/kubernetes/kubernetes/pull/59948
            pod = self._get_pod_by_metric_label(sample[self.SAMPLE_LABELS])
            if pod is not None and is_static_pending_pod(pod):
                tags += get_tags('kubernetes_pod://%s' % pod["metadata"]["uid"], True)
                tags += self._get_kube_container_name(sample[self.SAMPLE_LABELS])
                tags = list(set(tags))

            val = sample[self.SAMPLE_VALUE]
            cache[c_name] = (val, tags)
            seen_keys[c_name] = True
            self.gauge(m_name, val, tags)

        # purge the cache
        for k, seen in seen_keys.iteritems():
            if not seen:
                del cache[k]

    def _process_limit_metric(self, m_name, metric, cache, scraper_config, pct_m_name=None):
        """
        Reports limit metrics if m_name is not an empty string,
        and optionally checks in the given cache if there's a usage
        for each sample in the metric and reports the usage_pct
        """
        samples = self._sum_values_by_context(metric, self._get_container_id_if_container_metric)
        for c_id, sample in samples.iteritems():
            limit = sample[self.SAMPLE_VALUE]
            pod_uid = self._get_pod_uid(sample[self.SAMPLE_LABELS])
            if self.pod_list_utils.is_excluded(c_id, pod_uid):
                continue

            tags = get_tags(c_id, True)
            tags += scraper_config['custom_tags']

            if m_name:
                self.gauge(m_name, limit, tags)

            if pct_m_name and limit > 0:
                c_name = self._get_container_label(sample[self.SAMPLE_LABELS], 'name')
                if not c_name:
                    continue
                usage, tags = cache.get(c_name, (None, None))
                if usage:
                    self.gauge(pct_m_name, float(usage / float(limit)), tags)
                else:
                    self.log.debug("No corresponding usage found for metric %s and "
                                   "container %s, skipping usage_pct for now." % (pct_m_name, c_name))

    def container_cpu_usage_seconds_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.cpu.usage.total'

        for i, sample in enumerate(metric.samples):
            # Replacing the sample tuple to convert cores in nano cores
            metric.samples[i] = (sample[self.SAMPLE_NAME], sample[self.SAMPLE_LABELS],
                                 sample[self.SAMPLE_VALUE] * 10. ** 9)

        self._process_container_rate(metric_name, metric, scraper_config)

    def container_fs_reads_bytes_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.io.read_bytes'
        self._process_container_rate(metric_name, metric, scraper_config)

    def container_fs_writes_bytes_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.io.write_bytes'
        self._process_container_rate(metric_name, metric, scraper_config)

    def container_network_receive_bytes_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.network.rx_bytes'
        self._process_pod_rate(metric_name, metric, scraper_config)

    def container_network_transmit_bytes_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.network.tx_bytes'
        self._process_pod_rate(metric_name, metric, scraper_config)

    def container_network_receive_errors_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.network.rx_errors'
        self._process_pod_rate(metric_name, metric, scraper_config)

    def container_network_transmit_errors_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.network.tx_errors'
        self._process_pod_rate(metric_name, metric, scraper_config)

    def container_network_transmit_packets_dropped_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.network.tx_dropped'
        self._process_pod_rate(metric_name, metric, scraper_config)

    def container_network_receive_packets_dropped_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.network.rx_dropped'
        self._process_pod_rate(metric_name, metric, scraper_config)

    def container_fs_usage_bytes(self, metric, scraper_config):
        """
        Number of bytes that are consumed by the container on this filesystem.
        """
        metric_name = scraper_config['namespace'] + '.filesystem.usage'
        if metric.type not in METRIC_TYPES:
            self.log.error("Metric type %s unsupported for metric %s" % (metric.type, metric.name))
            return
        self._process_usage_metric(metric_name, metric, self.fs_usage_bytes, scraper_config)

    def container_fs_limit_bytes(self, metric, scraper_config):
        """
        Number of bytes that can be consumed by the container on this filesystem.
        This method is used by container_fs_usage_bytes, it doesn't report any metric
        """
        pct_m_name = scraper_config['namespace'] + '.filesystem.usage_pct'
        if metric.type not in METRIC_TYPES:
            self.log.error("Metric type %s unsupported for metric %s" % (metric.type, metric.name))
            return
        self._process_limit_metric('', metric, self.fs_usage_bytes, scraper_config, pct_m_name)

    def container_memory_usage_bytes(self, metric, scraper_config):
        """TODO: add swap, cache, failcnt and rss"""
        metric_name = scraper_config['namespace'] + '.memory.usage'
        if metric.type not in METRIC_TYPES:
            self.log.error("Metric type %s unsupported for metric %s" % (metric.type, metric.name))
            return
        self._process_usage_metric(metric_name, metric, self.mem_usage_bytes, scraper_config)

    def container_spec_memory_limit_bytes(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.memory.limits'
        pct_m_name = scraper_config['namespace'] + '.memory.usage_pct'
        if metric.type not in METRIC_TYPES:
            self.log.error("Metric type %s unsupported for metric %s" % (metric.type, metric.name))
            return
        self._process_limit_metric(metric_name, metric, self.mem_usage_bytes, scraper_config, pct_m_name=pct_m_name)
