import json
import os
import sys
from typing import Dict, List

INTEGRATIONS_CORE = os.environ['INTEGRATIONS_CORE_ROOT']
INTEGRATIONS_EXTRAS = os.environ['INTEGRATIONS_EXTRAS_ROOT']
CONSUL_INTEGRATIONS = os.environ['CONSUL_INTEGRATIONS']
CONSUL_ROOT = os.environ['CONSUL_ROOT']

# Integrations or folder not having their own tile
INTEGRATIONS_EXCEPTIONS = [
    # Datadog exceptions, not integrations
    'agent_metrics',
    'datadog_checks_base',
    'datadog_checks_dev',
    'datadog_checks_dependency_provider',
    'datadog_checks_downloader',
    'datadog_checks_tests_helper',
    'datadog_cluster_agent',
    'docs',
    # Integrations exceptions
    'activemq_xml',
    'cassandra_nodetool',
    'cloud_foundry_api',
    'dns_check',
    'docker',
    'eks_fargate',
    'external_dns',
    'gke',
    'gnatsd',  # Extras with gnatsd_streaming
    'gnatsd_streaming',  # Extras with gnatsd
    'go-metro',
    'hbase_master',  # Extras with hbase_regionserver?
    'hbase_regionserver',  # Extras with hbase_master?
    'hdfs_namenode',
    'http_check',  # network
    'kafka_consumer',
    'kubelet',
    'kube_apiserver_metrics',
    'kube_dns',
    'kube_proxy',
    'kubernetes_state',
    'mesos_slave',
    'ntp',
    'oom_kill',
    'openstack_controller',
    'snmpwalk',
    'ssh_check',
    'tcp_queue_length',
    'win32_event_log',
    # System integrations
    'directory',
    'disk',
    'linux_proc_extras',
    'network',
    'docker_daemon',
    'nfsstat',
    'process',
    'system_swap',
    'system_core',
    'tcp_check',
]


def get_all_repo_integrations(root: str) -> List[str]:
    """
    List all the directory in an integrations repository without the exceptions
    """
    integrations_dirs = [
        d
        for d in os.listdir(root)
        if os.path.isdir(os.path.join(root, d)) and not d.startswith('.') and d not in INTEGRATIONS_EXCEPTIONS
    ]

    return integrations_dirs


def check_sync_consul(name1: str, dirs1: Dict[str, List[str]], name2: str, dirs2: Dict[str, List[str]]) -> List[str]:
    if len(dirs1['names']) > len(dirs2['names']):
        diff = set(dirs1['names']) - set(dirs2['names'])
        return [f"Missing sync in {name2}: {diff}"]
    if len(dirs1['names']) < len(dirs2['names']):
        diff = set(dirs1['names']) - set(dirs1['names'])
        return [f"Missing sync in {name1}: {diff}"]
    errors = []
    for i in range(len(dirs1['paths'])):
        file1 = open(dirs1['paths'][i]).read()
        file2 = open(dirs2['paths'][i]).read()
        if file1 != file2:
            errors.append(f"Out of sync: {dirs1['paths'][i]} and {dirs2['paths'][i]}")
    return errors


def check_integrations(integrations: List[str], names: List[str]) -> str:
    """
    Check integration tiles exist somewhere
    """
    if len(integrations) > len(names):
        return f"Integrations not synced: {sorted(set(integrations) - set(names))}"
    return ""


def get_integration_id(name: str) -> str:
    """
    Integration name is the integration_id defined in the manifest.json
    """
    core = os.path.join(INTEGRATIONS_CORE, name, 'manifest.json')
    if os.path.exists(core):
        manifest = open(core)
    else:
        manifest = open(os.path.join(INTEGRATIONS_EXTRAS, name, 'manifest.json'))
    integration_id = json.load(manifest)['integration_id']

    return integration_id.replace('_', '-')


if __name__ == '__main__':
    integrations = sorted(get_all_repo_integrations(INTEGRATIONS_CORE) + get_all_repo_integrations(INTEGRATIONS_EXTRAS))
    consuls = CONSUL_INTEGRATIONS.split(';')
    integrations_id = []

    assert len(consuls) > 0
    assert len(integrations) > 0

    for i in range(len(integrations)):
        integrations_id.append(get_integration_id(integrations[i]))

    dirs = {}
    for p in consuls:
        full_path = os.path.join(CONSUL_ROOT, p)
        dir = list(set(integrations_id).intersection(set(os.listdir(full_path))))
        assert len(dir) > 0
        dirs[p] = {'names': sorted(dir)}
        dirs[p]['paths'] = [os.path.join(full_path, i) for i in dirs[p]['names']]

    errors = []
    for c1 in range(len(consuls)):
        for c2 in range(c1 + 1, len(consuls)):
            name1 = consuls[c1]
            name2 = consuls[c2]
            errors += check_sync_consul(name1, dirs[name1], name2, dirs[name2])
    errors.append(check_integrations(integrations_id, dirs[consuls[0]]['names']))

    for err in errors:
        print(err, file=sys.stderr)
