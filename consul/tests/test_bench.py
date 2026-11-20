# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from datadog_checks.consul import ConsulCheck

from . import common, consul_mocks


@pytest.mark.parametrize('num_nodes', [1000, 2000])
@pytest.mark.parametrize('sample_size', [None, 256])
def test_check_network_latency(benchmark: BenchmarkFixture, num_nodes: int, sample_size: int | None):
    config = dict(consul_mocks.MOCK_CONFIG_NETWORK_LATENCY_CHECKS, network_latency_sample_size=sample_size)
    consul_check = ConsulCheck(common.CHECK_NAME, {}, [config])
    my_mocks = consul_mocks._get_consul_mocks()
    consul_mocks.mock_check(consul_check, my_mocks)

    nodes = consul_mocks.mock_get_coord_nodes_benchmark(num_nodes)
    consul_check._get_coord_nodes = lambda: nodes

    # We start out as the leader, and stay that way
    consul_check._last_known_leader = consul_mocks.mock_get_cluster_leader_A()

    agent_dc = consul_check._get_agent_datacenter()
    tags = ['consul_datacenter:{}'.format(agent_dc)]

    benchmark(consul_check.check_network_latency, agent_dc, tags)
