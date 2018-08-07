# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

"""kubernetes check
Collects metrics from cAdvisor instance
"""
# stdlib
from fnmatch import fnmatch
import numbers
from urlparse import urlparse
import logging

# 3p
import requests

# check
from .common import tags_for_docker, tags_for_pod, is_static_pending_pod, get_pod_by_uid
from tagger import get_tags

NAMESPACE = "kubernetes"
DEFAULT_MAX_DEPTH = 10
DEFAULT_ENABLED_RATES = [
    'diskio.io_service_bytes.stats.total',
    'network.??_bytes',
    'cpu.*.total']
DEFAULT_ENABLED_GAUGES = [
    'memory.usage',
    'filesystem.usage']
DEFAULT_POD_LEVEL_METRICS = [
    'network.*']

NET_ERRORS = ['rx_errors', 'tx_errors', 'rx_dropped', 'tx_dropped']

LEGACY_CADVISOR_METRICS_PATH = '/api/v1.3/subcontainers/'


class CadvisorScraper(object):
    """
    CadvisorScraper is a mixin intended to be inherited by an AgentCheck
    class, as it uses its AgentCheck facilities and class members.
    It is not possible to run it standalone.
    """
    def __init__(self, *args, **kwargs):
        super(CadvisorScraper, self).__init__(*args, **kwargs)

        # The scraper needs its own logger
        self.log = logging.getLogger(__name__)

    @staticmethod
    def detect_cadvisor(kubelet_url, cadvisor_port):
        """
        Tries to connect to the cadvisor endpoint, with given params
        :return: url if OK, raises exception if NOK
        """
        if cadvisor_port == 0:
            raise ValueError("cAdvisor port set to 0 in configuration")
        kubelet_hostname = urlparse(kubelet_url).hostname
        if not kubelet_hostname:
            raise ValueError("kubelet hostname empty")
        url = "http://{}:{}{}".format(kubelet_hostname, cadvisor_port,
                                      LEGACY_CADVISOR_METRICS_PATH)

        # Test the endpoint is present
        r = requests.head(url, timeout=1)
        r.raise_for_status()

        return url

    def process_cadvisor(self, instance, cadvisor_url, pod_list, pod_list_utils):
        """
        Scrape and submit metrics from cadvisor
        :param: instance: check instance object
        :param: cadvisor_url: valid cadvisor url, as returned by detect_cadvisor()
        :param: pod_list: fresh podlist object from the kubelet
        :param: pod_list_utils: already initialised PodListUtils object
        """
        self.max_depth = instance.get('max_depth', DEFAULT_MAX_DEPTH)
        enabled_gauges = instance.get('enabled_gauges', DEFAULT_ENABLED_GAUGES)
        self.enabled_gauges = ["{0}.{1}".format(NAMESPACE, x) for x in enabled_gauges]
        enabled_rates = instance.get('enabled_rates', DEFAULT_ENABLED_RATES)
        self.enabled_rates = ["{0}.{1}".format(NAMESPACE, x) for x in enabled_rates]
        pod_level_metrics = instance.get('pod_level_metrics', DEFAULT_POD_LEVEL_METRICS)
        self.pod_level_metrics = ["{0}.{1}".format(NAMESPACE, x) for x in pod_level_metrics]

        self._update_metrics(instance, cadvisor_url, pod_list, pod_list_utils)

    @staticmethod
    def _retrieve_cadvisor_metrics(cadvisor_url, timeout=10):
        return requests.get(cadvisor_url, timeout=timeout).json()

    def _update_metrics(self, instance, cadvisor_url, pod_list, pod_list_utils):
        metrics = self._retrieve_cadvisor_metrics(cadvisor_url)

        if not metrics:
            self.warning('cAdvisor returned no metrics')
            return

        for subcontainer in metrics:
            c_id = subcontainer.get('id')
            if 'aliases' not in subcontainer:
                # it means the subcontainer is about a higher-level entity than a container
                continue
            try:
                self._update_container_metrics(instance, subcontainer, pod_list, pod_list_utils)
            except Exception as e:
                self.log.error("Unable to collect metrics for container: {0} ({1})".format(c_id, e))

    def _publish_raw_metrics(self, metric, dat, tags, is_pod, depth=0):
        """
        Recusively parses and submit metrics for a given entity, until
        reaching self.max_depth.
        Nested metric names are flattened: memory/usage -> memory.usage
        :param: metric: parent's metric name (check namespace for root stat objects)
        :param: dat: metric dictionnary to parse
        :param: tags: entity tags to use when submitting
        :param: is_pod: is the entity a pod (bool)
        :param: depth: current depth of recursion
        """
        if depth >= self.max_depth:
            self.log.warning('Reached max depth on metric=%s' % metric)
            return

        if isinstance(dat, numbers.Number):
            # Pod level metric filtering
            is_pod_metric = False
            if self.pod_level_metrics and any([fnmatch(metric, pat) for pat in self.pod_level_metrics]):
                is_pod_metric = True
            if is_pod_metric != is_pod:
                return

            # Metric submission
            if self.enabled_rates and any([fnmatch(metric, pat) for pat in self.enabled_rates]):
                self.rate(metric, float(dat), tags)
            elif self.enabled_gauges and any([fnmatch(metric, pat) for pat in self.enabled_gauges]):
                self.gauge(metric, float(dat), tags)

        elif isinstance(dat, dict):
            for k, v in dat.iteritems():
                self._publish_raw_metrics(metric + '.%s' % k.lower(), v, tags, is_pod, depth + 1)

        elif isinstance(dat, list):
            self._publish_raw_metrics(metric, dat[-1], tags, is_pod, depth + 1)

    def _update_container_metrics(self, instance, subcontainer, pod_list, pod_list_utils):
        is_pod = False
        in_static_pod = False
        subcontainer_id = subcontainer.get('id')
        pod_uid = subcontainer.get('labels', {}).get('io.kubernetes.pod.uid')
        k_container_name = subcontainer.get('labels', {}).get('io.kubernetes.container.name')

        # We want to collect network metrics at the pod level
        if k_container_name == "POD" and pod_uid:
            is_pod = True

        # FIXME we are forced to do that because the Kubelet PodList isn't updated
        # for static pods, see https://github.com/kubernetes/kubernetes/pull/59948
        pod = get_pod_by_uid(pod_uid, pod_list)
        if pod is not None and is_static_pending_pod(pod):
            in_static_pod = True

        # Let's see who we have here
        if is_pod:
            tags = tags_for_pod(pod_uid, True)
        elif in_static_pod and k_container_name:
            # FIXME static pods don't have container statuses so we can't
            # get the container id with the scheme, assuming docker here
            tags = tags_for_docker(subcontainer_id, True)
            tags += tags_for_pod(pod_uid, True)
            tags.append("kube_container_name:%s" % k_container_name)
        else:  # Standard container
            cid = pod_list_utils.get_cid_by_name_tuple(
                (pod.get('metadata', {}).get('namespace', ""),
                 pod.get('metadata', {}).get('name', ""), k_container_name))
            if pod_list_utils.is_excluded(cid):
                self.log.debug("Filtering out " + cid)
                return
            tags = get_tags(cid, True)

        if not tags:
            self.log.debug("Subcontainer {} doesn't have tags, skipping.".format(subcontainer_id))
            return
        tags = list(set(tags + instance.get('tags', [])))

        stats = subcontainer['stats'][-1]  # take the latest
        self._publish_raw_metrics(NAMESPACE, stats, tags, is_pod)

        if is_pod is False and subcontainer.get("spec", {}).get("has_filesystem") and stats.get('filesystem'):
            fs = stats['filesystem'][-1]
            fs_utilization = float(fs['usage']) / float(fs['capacity'])
            self.gauge(NAMESPACE + '.filesystem.usage_pct', fs_utilization, tags=tags)

        if is_pod and subcontainer.get("spec", {}).get("has_network"):
            net = stats['network']
            self.rate(NAMESPACE + '.network_errors', sum(float(net[x]) for x in NET_ERRORS), tags=tags)
