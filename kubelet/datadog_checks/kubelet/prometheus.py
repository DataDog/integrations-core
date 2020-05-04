# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import division

from copy import deepcopy

from six import iteritems

from datadog_checks.base.checks.openmetrics import OpenMetricsBaseCheck
from datadog_checks.base.utils.tagging import tagger

from .common import get_pod_by_uid, is_static_pending_pod, replace_container_rt_prefix

METRIC_TYPES = ['counter', 'gauge', 'summary']

# container-specific metrics should have all these labels
PRE_1_16_CONTAINER_LABELS = set(['namespace', 'name', 'image', 'id', 'container_name', 'pod_name'])
POST_1_16_CONTAINER_LABELS = set(['namespace', 'name', 'image', 'id', 'container', 'pod'])


class CadvisorPrometheusScraperMixin(object):
    """
    This class scrapes metrics for the kubelet "/metrics/cadvisor" prometheus endpoint and submits
    them on behalf of a check.
    """

    def __init__(self, *args, **kwargs):
        super(CadvisorPrometheusScraperMixin, self).__init__(*args, **kwargs)

        # these are filled by container_<metric-name>_usage_<metric-unit>
        # and container_<metric-name>_limit_<metric-unit> reads it to compute <metric-name>usage_pct
        self.fs_usage_bytes = {}
        self.mem_usage_bytes = {}
        self.swap_usage_bytes = {}

        self.CADVISOR_METRIC_TRANSFORMERS = {
            'container_cpu_usage_seconds_total': self.container_cpu_usage_seconds_total,
            'container_cpu_load_average_10s': self.container_cpu_load_average_10s,
            'container_cpu_system_seconds_total': self.container_cpu_system_seconds_total,
            'container_cpu_user_seconds_total': self.container_cpu_user_seconds_total,
            'container_cpu_cfs_periods_total': self.container_cpu_cfs_periods_total,
            'container_cpu_cfs_throttled_periods_total': self.container_cpu_cfs_throttled_periods_total,
            'container_cpu_cfs_throttled_seconds_total': self.container_cpu_cfs_throttled_seconds_total,
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
            'container_memory_working_set_bytes': self.container_memory_working_set_bytes,
            'container_memory_cache': self.container_memory_cache,
            'container_memory_rss': self.container_memory_rss,
            'container_memory_swap': self.container_memory_swap,
            'container_spec_memory_limit_bytes': self.container_spec_memory_limit_bytes,
            'container_spec_memory_swap_limit_bytes': self.container_spec_memory_swap_limit_bytes,
        }

    def _create_cadvisor_prometheus_instance(self, instance):
        """
        Create a copy of the instance and set default values.
        This is so the base class can create a scraper_config with the proper values.
        """
        cadvisor_instance = deepcopy(instance)
        cadvisor_instance.update(
            {
                'namespace': self.NAMESPACE,
                # We need to specify a prometheus_url so the base class can use it as the key for our config_map,
                # we specify a dummy url that will be replaced in the `check()` function. We append it with "cadvisor"
                # so the key is different than the kubelet scraper.
                'prometheus_url': instance.get('cadvisor_metrics_endpoint', 'dummy_url/cadvisor'),
                'ignore_metrics': [
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
                    'container_scrape_error',
                ],
                # Defaults that were set when CadvisorPrometheusScraper was based on PrometheusScraper
                'send_monotonic_counter': instance.get('send_monotonic_counter', False),
                'health_service_check': instance.get('health_service_check', False),
            }
        )
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
        label_set = set(labels)
        if POST_1_16_CONTAINER_LABELS.issubset(label_set):
            if labels.get('container') in ['', 'POD']:
                return False
        elif PRE_1_16_CONTAINER_LABELS.issubset(label_set):
            if labels.get('container_name') in ['', 'POD']:
                return False
        else:
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
        # k8s >= 1.16
        # docker reports container==POD (first case), containerd does not (second case)
        if labels.get('container') == 'POD' or (labels.get('container') == '' and labels.get('pod', False)):
            return True
        # k8s < 1.16 && > 1.8
        if labels.get('container_name') == 'POD' or (
            labels.get('container_name') == '' and labels.get('pod_name', False)
        ):
            return True
        # k8s < 1.8
        # container_cpu_usage_seconds_total has an id label that is a cgroup path
        # eg: /kubepods/burstable/pod531c80d9-9fc4-11e7-ba8b-42010af002bb
        # FIXME: this was needed because of a bug:
        # https://github.com/kubernetes/kubernetes/pull/51473
        if labels.get('id', '').split('/')[-1].startswith('pod'):
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
        # k8s >= 1.16
        pod_name = CadvisorPrometheusScraperMixin._get_container_label(labels, "pod")
        container_name = CadvisorPrometheusScraperMixin._get_container_label(labels, "container")
        # k8s < 1.16
        if not pod_name:
            pod_name = CadvisorPrometheusScraperMixin._get_container_label(labels, "pod_name")
        if not container_name:
            container_name = CadvisorPrometheusScraperMixin._get_container_label(labels, "container_name")
        return self.pod_list_utils.get_cid_by_name_tuple((namespace, pod_name, container_name))

    def _get_entity_id_if_container_metric(self, labels):
        """
        Checks the labels indicate a container metric,
        then extract the container id from them.

        :param labels
        :return str or None
        """
        if CadvisorPrometheusScraperMixin._is_container_metric(labels):
            pod = self._get_pod_by_metric_label(labels)
            if pod is not None and is_static_pending_pod(pod):
                # If the pod is static, ContainerStatus is unavailable.
                # Return the pod UID so that we can collect metrics from it later on.
                return self._get_pod_uid(labels)
            return self._get_container_id(labels)

    def _get_pod_uid(self, labels):
        """
        Return the id of a pod
        :param labels:
        :return: str or None
        """
        namespace = CadvisorPrometheusScraperMixin._get_container_label(labels, "namespace")
        pod_name = CadvisorPrometheusScraperMixin._get_container_label(labels, "pod")
        # k8s < 1.16
        if not pod_name:
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
        container_name = CadvisorPrometheusScraperMixin._get_container_label(labels, "container")
        # k8s < 1.16
        if not container_name:
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
                    seen[uid][OpenMetricsBaseCheck.SAMPLE_VALUE] + sample[OpenMetricsBaseCheck.SAMPLE_VALUE],
                )
                # TODO
                # metric.Clear()  # Ignore this metric message
        return seen

    def _process_container_metric(self, type, metric_name, metric, scraper_config, labels=None):
        """
        Takes a simple metric about a container, reports it as a rate or gauge.
        If several series are found for a given container, values are summed before submission.
        """
        if labels is None:
            labels = []

        if metric.type not in METRIC_TYPES:
            self.log.error("Metric type %s unsupported for metric %s", metric.type, metric.name)
            return

        samples = self._sum_values_by_context(metric, self._get_entity_id_if_container_metric)
        for c_id, sample in iteritems(samples):
            pod_uid = self._get_pod_uid(sample[self.SAMPLE_LABELS])
            if self.pod_list_utils.is_excluded(c_id, pod_uid):
                continue

            tags = tagger.tag(replace_container_rt_prefix(c_id), tagger.HIGH)
            if not tags:
                continue
            tags += scraper_config['custom_tags']

            # FIXME we are forced to do that because the Kubelet PodList isn't updated
            # for static pods, see https://github.com/kubernetes/kubernetes/pull/59948
            pod = self._get_pod_by_metric_label(sample[self.SAMPLE_LABELS])
            if pod is not None and is_static_pending_pod(pod):
                pod_tags = tagger.tag('kubernetes_pod_uid://%s' % pod["metadata"]["uid"], tagger.HIGH)
                if not pod_tags:
                    continue
                tags += pod_tags
                tags += self._get_kube_container_name(sample[self.SAMPLE_LABELS])
                tags = list(set(tags))

            for label in labels:
                value = sample[self.SAMPLE_LABELS].get(label)
                if value:
                    tags.append('%s:%s' % (label, value))

            val = sample[self.SAMPLE_VALUE]

            if "rate" == type:
                self.rate(metric_name, val, tags)
            elif "gauge" == type:
                self.gauge(metric_name, val, tags)

    def _process_pod_rate(self, metric_name, metric, scraper_config, labels=None):
        """
        Takes a simple metric about a pod, reports it as a rate.
        If several series are found for a given pod, values are summed before submission.
        """
        if labels is None:
            labels = []

        if metric.type not in METRIC_TYPES:
            self.log.error("Metric type %s unsupported for metric %s", metric.type, metric.name)
            return

        samples = self._sum_values_by_context(metric, self._get_pod_uid_if_pod_metric)
        for pod_uid, sample in iteritems(samples):
            if '.network.' in metric_name and self._is_pod_host_networked(pod_uid):
                continue
            tags = tagger.tag('kubernetes_pod_uid://%s' % pod_uid, tagger.HIGH)
            if not tags:
                continue
            tags += scraper_config['custom_tags']
            for label in labels:
                value = sample[self.SAMPLE_LABELS].get(label)
                if value:
                    tags.append('%s:%s' % (label, value))
            val = sample[self.SAMPLE_VALUE]
            self.rate(metric_name, val, tags)

    def _process_usage_metric(self, m_name, metric, cache, scraper_config, labels=None):
        """
        Takes a metric object, a metric name, and a cache dict where it will store
        container_name --> (value, tags) so that _process_limit_metric can compute usage_pct
        it also submit said value and tags as a gauge.
        """
        if labels is None:
            labels = []

        # track containers that still exist in the cache
        seen_keys = {k: False for k in cache}

        samples = self._sum_values_by_context(metric, self._get_entity_id_if_container_metric)
        for c_id, sample in iteritems(samples):
            c_name = self._get_container_label(sample[self.SAMPLE_LABELS], 'name')
            if not c_name:
                continue
            pod_uid = self._get_pod_uid(sample[self.SAMPLE_LABELS])
            if self.pod_list_utils.is_excluded(c_id, pod_uid):
                continue

            tags = tagger.tag(replace_container_rt_prefix(c_id), tagger.HIGH)
            if not tags:
                continue
            tags += scraper_config['custom_tags']

            # FIXME we are forced to do that because the Kubelet PodList isn't updated
            # for static pods, see https://github.com/kubernetes/kubernetes/pull/59948
            pod = self._get_pod_by_metric_label(sample[self.SAMPLE_LABELS])
            if pod is not None and is_static_pending_pod(pod):
                pod_tags = tagger.tag('kubernetes_pod_uid://%s' % pod["metadata"]["uid"], tagger.HIGH)
                if not pod_tags:
                    continue
                tags += pod_tags
                tags += self._get_kube_container_name(sample[self.SAMPLE_LABELS])
                tags = list(set(tags))

            for label in labels:
                value = sample[self.SAMPLE_LABELS].get(label)
                if value:
                    tags.append('%s:%s' % (label, value))

            val = sample[self.SAMPLE_VALUE]
            cache[c_name] = (val, tags)
            seen_keys[c_name] = True
            self.gauge(m_name, val, tags)

        # purge the cache
        for k, seen in iteritems(seen_keys):
            if not seen:
                del cache[k]

    def _process_limit_metric(self, m_name, metric, cache, scraper_config, pct_m_name=None):
        """
        Reports limit metrics if m_name is not an empty string,
        and optionally checks in the given cache if there's a usage
        for each sample in the metric and reports the usage_pct
        """
        samples = self._sum_values_by_context(metric, self._get_entity_id_if_container_metric)
        for c_id, sample in iteritems(samples):
            limit = sample[self.SAMPLE_VALUE]
            pod_uid = self._get_pod_uid(sample[self.SAMPLE_LABELS])
            if self.pod_list_utils.is_excluded(c_id, pod_uid):
                continue

            tags = tagger.tag(replace_container_rt_prefix(c_id), tagger.HIGH)
            if not tags:
                continue
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
                    self.log.debug(
                        "No corresponding usage found for metric %s and container %s, skipping usage_pct for now.",
                        pct_m_name,
                        c_name,
                    )

    def container_cpu_usage_seconds_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.cpu.usage.total'

        for i, sample in enumerate(metric.samples):
            # Replacing the sample tuple to convert cores in nano cores
            metric.samples[i] = (
                sample[self.SAMPLE_NAME],
                sample[self.SAMPLE_LABELS],
                sample[self.SAMPLE_VALUE] * 10.0 ** 9,
            )
        self._process_container_metric('rate', metric_name, metric, scraper_config)

    def container_cpu_load_average_10s(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.cpu.load.10s.avg'
        self._process_container_metric('gauge', metric_name, metric, scraper_config)

    def container_cpu_system_seconds_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.cpu.system.total'
        self._process_container_metric('rate', metric_name, metric, scraper_config)

    def container_cpu_user_seconds_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.cpu.user.total'
        self._process_container_metric('rate', metric_name, metric, scraper_config)

    def container_cpu_cfs_periods_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.cpu.cfs.periods'
        self._process_container_metric('rate', metric_name, metric, scraper_config)

    def container_cpu_cfs_throttled_periods_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.cpu.cfs.throttled.periods'
        self._process_container_metric('rate', metric_name, metric, scraper_config)

    def container_cpu_cfs_throttled_seconds_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.cpu.cfs.throttled.seconds'
        self._process_container_metric('rate', metric_name, metric, scraper_config)

    def container_fs_reads_bytes_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.io.read_bytes'
        labels = ['device']
        self._process_container_metric('rate', metric_name, metric, scraper_config, labels=labels)

    def container_fs_writes_bytes_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.io.write_bytes'
        labels = ['device']
        self._process_container_metric('rate', metric_name, metric, scraper_config, labels=labels)

    def container_network_receive_bytes_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.network.rx_bytes'
        labels = ['interface']
        self._process_pod_rate(metric_name, metric, scraper_config, labels=labels)

    def container_network_transmit_bytes_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.network.tx_bytes'
        labels = ['interface']
        self._process_pod_rate(metric_name, metric, scraper_config, labels=labels)

    def container_network_receive_errors_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.network.rx_errors'
        labels = ['interface']
        self._process_pod_rate(metric_name, metric, scraper_config, labels=labels)

    def container_network_transmit_errors_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.network.tx_errors'
        labels = ['interface']
        self._process_pod_rate(metric_name, metric, scraper_config, labels=labels)

    def container_network_transmit_packets_dropped_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.network.tx_dropped'
        labels = ['interface']
        self._process_pod_rate(metric_name, metric, scraper_config, labels=labels)

    def container_network_receive_packets_dropped_total(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.network.rx_dropped'
        labels = ['interface']
        self._process_pod_rate(metric_name, metric, scraper_config, labels=labels)

    def container_fs_usage_bytes(self, metric, scraper_config):
        """
        Number of bytes that are consumed by the container on this filesystem.
        """
        metric_name = scraper_config['namespace'] + '.filesystem.usage'
        if metric.type not in METRIC_TYPES:
            self.log.error("Metric type %s unsupported for metric %s", metric.type, metric.name)
            return
        labels = ['device']
        self._process_usage_metric(metric_name, metric, self.fs_usage_bytes, scraper_config, labels=labels)

    def container_fs_limit_bytes(self, metric, scraper_config):
        """
        Number of bytes that can be consumed by the container on this filesystem.
        This method is used by container_fs_usage_bytes, it doesn't report any metric
        """
        pct_m_name = scraper_config['namespace'] + '.filesystem.usage_pct'
        if metric.type not in METRIC_TYPES:
            self.log.error("Metric type %s unsupported for metric %s", metric.type, metric.name)
            return
        self._process_limit_metric('', metric, self.fs_usage_bytes, scraper_config, pct_m_name)

    def container_memory_usage_bytes(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.memory.usage'
        if metric.type not in METRIC_TYPES:
            self.log.error("Metric type %s unsupported for metric %s", metric.type, metric.name)
            return
        self._process_usage_metric(metric_name, metric, self.mem_usage_bytes, scraper_config)

    def container_memory_working_set_bytes(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.memory.working_set'
        self._process_container_metric('gauge', metric_name, metric, scraper_config)

    def container_memory_cache(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.memory.cache'
        self._process_container_metric('gauge', metric_name, metric, scraper_config)

    def container_memory_rss(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.memory.rss'
        self._process_container_metric('gauge', metric_name, metric, scraper_config)

    def container_memory_swap(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.memory.swap'
        if metric.type not in METRIC_TYPES:
            self.log.error("Metric type %s unsupported for metric %s", metric.type, metric.name)
            return
        self._process_usage_metric(metric_name, metric, self.swap_usage_bytes, scraper_config)

    def container_spec_memory_limit_bytes(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.memory.limits'
        pct_m_name = scraper_config['namespace'] + '.memory.usage_pct'
        if metric.type not in METRIC_TYPES:
            self.log.error("Metric type %s unsupported for metric %s", metric.type, metric.name)
            return
        self._process_limit_metric(metric_name, metric, self.mem_usage_bytes, scraper_config, pct_m_name=pct_m_name)

    def container_spec_memory_swap_limit_bytes(self, metric, scraper_config):
        metric_name = scraper_config['namespace'] + '.memory.sw_limit'
        pct_m_name = scraper_config['namespace'] + '.memory.sw_in_use'
        if metric.type not in METRIC_TYPES:
            self.log.error("Metric type %s unsupported for metric %s", metric.type, metric.name)
            return
        self._process_limit_metric(metric_name, metric, self.swap_usage_bytes, scraper_config, pct_m_name=pct_m_name)
