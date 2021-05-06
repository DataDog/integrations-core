# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

try:
    import datadog_agent
except ImportError:
    from ...stubs import datadog_agent

from .. import AgentCheck
from .record import ElectionRecordAnnotation, ElectionRecordLease

# Import lazily to reduce memory footprint
client = config = None

# Known names of the leader election annotation,
# will be tried in the order of the list
ELECTION_ANNOTATION_NAMES = ["control-plane.alpha.kubernetes.io/leader"]

K8S_REQUEST_TIMEOUT = 30


class KubeLeaderElectionMixin(object):
    """
    This mixin uses the facilities of the AgentCheck class
    """

    def check_election_status(self, config):
        """
        Retrieves the leader-election annotation from a given object, and
        submits metrics and a service check.

        An integration warning is sent if the object is not retrievable,
        or no record is found. Monitors on the service-check should have
        no-data alerts enabled to account for this.

        The config objet requires the following fields:
            namespace (prefix for the metrics and check)
            record_kind (leases, endpoints or configmap)
            record_name
            record_namespace
            tags (optional)

        It reads the following agent configuration:
            kubernetes_kubeconfig_path: defaut is to use in-cluster config
        """
        try:
            record = self._get_record(
                config.get("record_kind", ""), config.get("record_name", ""), config.get("record_namespace", "")
            )
            self._report_status(config, record)
        except Exception as e:
            self.warning("Cannot retrieve leader election record %s: %s", config.get("record_name", ""), e)

    @staticmethod
    def _get_record(kind, name, namespace):
        global client, config
        if client is config is None:
            from kubernetes import client, config  # noqa F401

        kubeconfig_path = datadog_agent.get_config('kubernetes_kubeconfig_path')
        if kubeconfig_path:
            config.load_kube_config(config_file=kubeconfig_path)
        else:
            config.load_incluster_config()

        if kind.lower() == "auto":
            # Try lease object
            try:
                return KubeLeaderElectionMixin._get_record_from_lease(client, name, namespace)
            except client.exceptions.ApiException:
                pass

            # Default to endpoints object
            return KubeLeaderElectionMixin._get_record_from_annotation(client, "endpoints", name, namespace)

        elif kind.lower() in ["leases", "lease"]:
            return KubeLeaderElectionMixin._get_record_from_lease(client, name, namespace)
        else:
            return KubeLeaderElectionMixin._get_record_from_annotation(client, kind, name, namespace)

    @staticmethod
    def _get_record_from_lease(client, name, namespace):
        coordination_v1 = client.CoordinationV1Api()
        obj = coordination_v1.read_namespaced_lease(name, namespace, _request_timeout=K8S_REQUEST_TIMEOUT)

        return ElectionRecordLease(obj)

    @staticmethod
    def _get_record_from_annotation(client, kind, name, namespace):
        v1 = client.CoreV1Api()

        if kind.lower() in ["endpoints", "endpoint", "ep"]:
            obj = v1.read_namespaced_endpoints(name, namespace, _request_timeout=K8S_REQUEST_TIMEOUT)
        elif kind.lower() in ["configmap", "cm"]:
            obj = v1.read_namespaced_config_map(name, namespace, _request_timeout=K8S_REQUEST_TIMEOUT)
        else:
            raise ValueError("Unknown kind {}".format(kind))

        if not obj:
            raise ValueError("Empty input object")

        try:
            annotations = obj.metadata.annotations
        except AttributeError:
            raise ValueError("Invalid input object type")

        for name in ELECTION_ANNOTATION_NAMES:
            if name in annotations:
                return ElectionRecordAnnotation(kind, annotations[name])

        # Could not find annotation
        raise ValueError("Object has no leader election annotation")

    def _report_status(self, config, record):
        # Compute prefix for gauges and service check
        prefix = config.get("namespace") + ".leader_election"

        # Compute tags for gauges and service check
        tags = []
        for k, v in {
            "record_kind": record.kind,
            "record_name": config.get("record_name"),
            "record_namespace": config.get("record_namespace"),
        }.items():
            if v is not None:
                tags.append("{}:{}".format(k, v))
        tags += config.get("tags", [])

        # Sanity check on the record
        valid, reason = record.validate()
        if not valid:
            self.service_check(prefix + ".status", AgentCheck.CRITICAL, tags=tags, message=reason)
            return  # Stop here

        # Report metrics
        self.monotonic_count(prefix + ".transitions", record.transitions, tags)
        self.gauge(prefix + ".lease_duration", record.lease_duration, tags)

        leader_status = AgentCheck.OK
        if record.seconds_until_renew + record.lease_duration < 0:
            leader_status = AgentCheck.CRITICAL
        self.service_check(prefix + ".status", leader_status, tags=tags, message=record.summary)
