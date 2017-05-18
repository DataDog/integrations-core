# (C) Datadog, Inc. 2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from checks import AgentCheck, CheckException
from utils.prometheus import parse_metric_family
from utils.kubernetes import KubeStateProcessor

import requests
import socket

KUBE_STATE_URL = 'kubernetes-state-metrics'

class KubernetesState(AgentCheck):
    """
    Collect metrics from kube-state-metrics API [0].

    [0] https://github.com/kubernetes/kube-state-metrics
    """
    def __init__(self, name, init_config, agentConfig, instances=None):
        super(KubernetesState, self).__init__(name, init_config, agentConfig, instances)
        self.kube_state_processor = KubeStateProcessor(self)

    def check(self, instance):
        self._update_kube_state_metrics(instance)

    def _update_kube_state_metrics(self, instance):
        """
        Retrieve the binary payload and process Prometheus metrics into
        Datadog metrics.
        """
        kube_state_url = instance.get('kube_state_url')
        if kube_state_url is None:
            # Try if kube-state-metrics resolves
            if socket.gethostbyname(KUBE_STATE_URL):
                kube_state_url = KUBE_STATE_URL
            else:
                raise CheckException("Unable to find kube_state_url in config file.")

        try:
            payload = self._get_kube_state(kube_state_url)
            msg = "Got a payload of size {} from Kube State API at url:{}".format(len(payload), kube_state_url)
            self.log.debug(msg)
            for metric in parse_metric_family(payload):
                self.kube_state_processor.process(metric, instance=instance)
        except Exception as e:
            self.log.error("Unable to retrieve metrics from Kube State API: {}".format(e))

    def _get_kube_state(self, endpoint):
        """
        Get metrics from the Kube State API using the protobuf format.
        """
        headers = {
            'accept': 'application/vnd.google.protobuf; proto=io.prometheus.client.MetricFamily; encoding=delimited',
            'accept-encoding': 'gzip',
        }
        req = requests.get(endpoint, headers=headers)
        req.raise_for_status()
        return req.content
