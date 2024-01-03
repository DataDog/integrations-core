# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

EXTRA_METRICS = [
    "felix.active.local_endpoints",
    "felix.active.local_policies",
    "felix.active.local_selectors",
    "felix.active.local_tags",
    "felix.cluster.num_host_endpoints",
    "felix.cluster.num_hosts",
    "felix.cluster.num_workload_endpoints",
    "felix.ipset.calls",
    "felix.ipset.errors",
    "felix.ipsets.calico",
    "felix.ipsets.total",
    "felix.iptables.chains",
    "felix.iptables.rules",
    "felix.iptables.restore_calls",
    "felix.iptables.restore_errors",
    "felix.iptables.save_calls",
    "felix.iptables.save_errors",
    "felix.int_dataplane_failures.count",
]

FORMATTED_EXTRA_METRICS = [
    "calico.felix.active.local_endpoints",
    "calico.felix.active.local_policies",
    "calico.felix.active.local_selectors",
    "calico.felix.cluster.num_host_endpoints",
    "calico.felix.cluster.num_hosts",
    "calico.felix.cluster.num_workload_endpoints",
    "calico.felix.ipset.calls.count",
    "calico.felix.ipset.errors.count",
    "calico.felix.ipsets.calico",
    "calico.felix.ipsets.total",
    "calico.felix.iptables.chains",
    "calico.felix.iptables.rules",
    "calico.felix.iptables.restore_calls.count",
    "calico.felix.iptables.restore_errors.count",
    "calico.felix.iptables.save_calls.count",
    "calico.felix.iptables.save_errors.count",
    "calico.felix.int_dataplane_failures.count",
]

MOCK_CALICO_INSTANCE = {
    "openmetrics_endpoint": 'http://localhost:9091/metrics',
    "namespace": "calico",
    "extra_metrics": EXTRA_METRICS,
}

OPTIONAL_METRICS = {
    'calico.felix.int_dataplane_failures.count',
    'calico.felix.ipset.calls.count',
    'calico.felix.ipset.errors.count',
    'calico.felix.iptables.restore_calls.count',
    'calico.felix.iptables.restore_errors.count',
    'calico.felix.iptables.save_calls.count',
    'calico.felix.iptables.save_errors.count',
}
