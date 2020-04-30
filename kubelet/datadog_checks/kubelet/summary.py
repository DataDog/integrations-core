# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import division

from datadog_checks.base.utils.tagging import tagger

from .common import replace_container_rt_prefix, tags_for_docker, tags_for_pod


class SummaryScraperMixin(object):
    """
    This class scrapes metrics from Kubelet "/stats/summary" endpoint
    """

    def process_stats_summary(self, pod_list_utils, stats, instance_tags, main_stats_source):
        # Reports system container metrics (node-wide)
        self._report_system_container_metrics(stats, instance_tags)
        # Reports POD & Container metrics. If `main_stats_source` is set, retrieve everything it can
        # Otherwise retrieves only what we cannot get elsewhere
        self._report_metrics(pod_list_utils, stats, instance_tags, main_stats_source)

    def _report_metrics(self, pod_list_utils, stats, instance_tags, main_stats_source):
        for pod in stats.get('pods', []):
            pod_namespace = pod.get('podRef', {}).get('namespace')
            pod_name = pod.get('podRef', {}).get('name')
            pod_uid = pod.get('podRef', {}).get('uid')

            if pod_namespace is None or pod_name is None or pod_uid is None:
                self.log.warning("Got incomplete results from '/stats/summary', missing data for POD: %s", pod)
                continue

            self._report_pod_stats(pod_namespace, pod_name, pod_uid, pod, instance_tags, main_stats_source)
            self._report_container_stats(
                pod_namespace, pod_name, pod.get('containers', []), pod_list_utils, instance_tags, main_stats_source
            )

    def _report_pod_stats(self, pod_namespace, pod_name, pod_uid, pod, instance_tags, main_stats_source):
        pod_tags = tags_for_pod(pod_uid, tagger.ORCHESTRATOR)
        if not pod_tags:
            self.log.debug("Tags not found for pod: %s/%s - no metrics will be sent", pod_namespace, pod_name)
            return
        pod_tags += instance_tags

        used_bytes = pod.get('ephemeral-storage', {}).get('usedBytes')
        if used_bytes:
            self.gauge(self.NAMESPACE + '.ephemeral_storage.usage', used_bytes, pod_tags)

        # Metrics below should already be gathered by another mean (cadvisor endpoints)
        if not main_stats_source:
            return

        rx_bytes = pod.get('network', {}).get('rxBytes')
        if rx_bytes:
            self.rate(self.NAMESPACE + '.network.rx_bytes', rx_bytes, pod_tags)
        tx_bytes = pod.get('network', {}).get('txBytes')
        if tx_bytes:
            self.rate(self.NAMESPACE + '.network.tx_bytes', tx_bytes, pod_tags)

    def _report_container_stats(
        self, pod_namespace, pod_name, containers, pod_list_utils, instance_tags, main_stats_source
    ):
        # Metrics below should already be gathered by another mean (cadvisor endpoints)
        if not main_stats_source:
            return

        for container in containers:
            container_name = container.get('name')
            if container_name is None:
                self.log.warning(
                    "Kubelet reported stats without container name for pod: %s/%s", pod_namespace, pod_name
                )
                continue

            # No mistake, we need to give a tuple as parameter
            container_id = pod_list_utils.get_cid_by_name_tuple((pod_namespace, pod_name, container_name))
            if container_id is None:
                self.log.debug(
                    "Container id not found from /pods for container: %s/%s/%s - no metrics will be sent",
                    pod_namespace,
                    pod_name,
                    container_name,
                )
                continue

            # TODO: In `containers` we also have terminated init-containers, probably to be excluded?
            if pod_list_utils.is_excluded(container_id):
                continue

            # Finally, we can get tags for this container
            container_tags = tags_for_docker(replace_container_rt_prefix(container_id), tagger.HIGH, True)
            if not container_tags:
                self.log.debug(
                    "Tags not found for container: %s/%s/%s:%s - no metrics will be sent",
                    pod_namespace,
                    pod_name,
                    container_name,
                    container_id,
                )
            container_tags += instance_tags

            cpu_total = container.get('cpu', {}).get('usageCoreNanoSeconds')
            if cpu_total:
                self.rate(self.NAMESPACE + '.cpu.usage.total', cpu_total, container_tags)

            working_set = container.get('memory', {}).get('workingSetBytes')
            if working_set:
                self.gauge(self.NAMESPACE + '.memory.working_set', working_set, container_tags)

            # TODO: Review meaning of these metrics as capacity != available + used
            # availableBytes = container.get('rootfs', {}).get('availableBytes')
            capacity_bytes = container.get('rootfs', {}).get('capacityBytes')
            used_bytes = container.get('rootfs', {}).get('usedBytes')

            if used_bytes is not None:
                self.gauge(self.NAMESPACE + '.filesystem.usage', used_bytes, container_tags)
            if used_bytes is not None and capacity_bytes is not None:
                self.gauge(self.NAMESPACE + '.filesystem.usage_pct', float(used_bytes) / capacity_bytes, container_tags)

    def _report_system_container_metrics(self, stats, instance_tags):
        sys_containers = stats.get('node', {}).get('systemContainers', [])
        for ctr in sys_containers:
            if ctr.get('name') == 'runtime':
                mem_rss = ctr.get('memory', {}).get('rssBytes')
                if mem_rss:
                    self.gauge(self.NAMESPACE + '.runtime.memory.rss', mem_rss, instance_tags)
                cpu_usage = ctr.get('cpu', {}).get('usageNanoCores')
                if cpu_usage:
                    self.gauge(self.NAMESPACE + '.runtime.cpu.usage', cpu_usage, instance_tags)
            if ctr.get('name') == 'kubelet':
                mem_rss = ctr.get('memory', {}).get('rssBytes')
                if mem_rss:
                    self.gauge(self.NAMESPACE + '.kubelet.memory.rss', mem_rss, instance_tags)
                cpu_usage = ctr.get('cpu', {}).get('usageNanoCores')
                if cpu_usage:
                    self.gauge(self.NAMESPACE + '.kubelet.cpu.usage', cpu_usage, instance_tags)
