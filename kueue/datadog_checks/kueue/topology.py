# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass

GPU_RESOURCE = 'nvidia.com/gpu'
NON_TERMINAL_POD_PHASES = {'Pending', 'Running'}


@dataclass(frozen=True)
class DomainStat:
    flavor: str
    level: str
    total: int
    available: int
    fully_used: int
    partially_used: int


@dataclass
class DomainResources:
    capacity: int = 0
    used: int = 0


def parse_gpu_quantity(value) -> int:
    if value is None:
        return 0

    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def build_node_gpu_usage(pods: list[dict]) -> dict[str, int]:
    node_gpu_usage = defaultdict(int)

    for pod in pods:
        spec = pod.get('spec', {})
        node_name = spec.get('nodeName')
        if not node_name or pod.get('status', {}).get('phase') not in NON_TERMINAL_POD_PHASES:
            continue

        gpu_request = pod_gpu_request(pod)
        if gpu_request > 0:
            node_gpu_usage[node_name] += gpu_request

    return dict(node_gpu_usage)


def pod_gpu_request(pod: dict) -> int:
    spec = pod.get('spec', {})
    container_request = sum(container_gpu_request(container) for container in spec.get('containers', []))
    init_container_request = max(
        (container_gpu_request(container) for container in spec.get('initContainers', [])), default=0
    )
    return max(container_request, init_container_request)


def container_gpu_request(container: dict) -> int:
    resource_requests = container.get('resources', {}).get('requests', {})
    return parse_gpu_quantity(resource_requests.get(GPU_RESOURCE))


def iter_domain_stats(
    nodes: list[dict],
    pods: list[dict],
    resource_flavors: list[dict],
    topologies: list[dict],
) -> Iterator[DomainStat]:
    topologies_by_name = {
        topology.get('metadata', {}).get('name'): topology
        for topology in topologies
        if topology.get('metadata', {}).get('name')
    }
    node_gpu_usage = build_node_gpu_usage(pods)

    for flavor in resource_flavors:
        flavor_name = flavor.get('metadata', {}).get('name')
        topology_name = flavor.get('spec', {}).get('topologyName')
        if not flavor_name or not topology_name:
            continue

        topology = topologies_by_name.get(topology_name)
        if topology is None:
            continue

        level_keys = topology_level_keys(topology)
        if not level_keys:
            continue

        flavor_nodes = [
            node
            for node in nodes
            if node_matches_labels(node, flavor.get('spec', {}).get('nodeLabels', {}))
            and node_has_topology_labels(node, level_keys)
        ]

        for level_index, level in enumerate(level_keys):
            domains = build_domain_resources(flavor_nodes, node_gpu_usage, level_keys, level_index)
            yield classify_domains(flavor_name, level, domains.values())


def topology_level_keys(topology: dict) -> list[str]:
    return [level['nodeLabel'] for level in topology.get('spec', {}).get('levels', []) if level.get('nodeLabel')]


def node_matches_labels(node: dict, labels: dict) -> bool:
    node_labels = node.get('metadata', {}).get('labels', {})
    return all(node_labels.get(key) == value for key, value in labels.items())


def node_has_topology_labels(node: dict, level_keys: list[str]) -> bool:
    labels = node.get('metadata', {}).get('labels', {})
    return all(level in labels for level in level_keys)


def build_domain_resources(
    nodes: list[dict],
    node_gpu_usage: dict[str, int],
    level_keys: list[str],
    level_index: int,
) -> dict[tuple[str, ...], DomainResources]:
    domains = defaultdict(DomainResources)

    for node in nodes:
        node_name = node.get('metadata', {}).get('name')
        labels = node.get('metadata', {}).get('labels', {})
        domain_path = tuple(labels[level] for level in level_keys[: level_index + 1])
        domain = domains[domain_path]
        domain.capacity += parse_gpu_quantity(node.get('status', {}).get('allocatable', {}).get(GPU_RESOURCE))
        domain.used += node_gpu_usage.get(node_name, 0)

    return dict(domains)


def classify_domains(flavor: str, level: str, domains: Iterator[DomainResources]) -> DomainStat:
    available = 0
    fully_used = 0
    partially_used = 0

    for domain in domains:
        if domain.capacity <= 0:
            continue
        if domain.used == 0:
            available += 1
        elif domain.used >= domain.capacity:
            fully_used += 1
        else:
            partially_used += 1

    return DomainStat(
        flavor=flavor,
        level=level,
        total=available + fully_used + partially_used,
        available=available,
        fully_used=fully_used,
        partially_used=partially_used,
    )
