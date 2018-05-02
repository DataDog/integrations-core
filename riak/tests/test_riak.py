# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import os
import subprocess
import requests
import socket
import time
import logging
from datadog_checks.riak import Riak
from datadog_checks.utils.common import get_docker_hostname

log = logging.getLogger('test_riak')

CHECK_NAME = 'riak'

CHECK_GAUGES = [
    'riak.node_gets',
    'riak.node_gets_total',
    'riak.node_puts',
    'riak.node_puts_total',
    'riak.node_gets_counter',
    'riak.node_gets_counter_total',
    'riak.node_gets_set',
    'riak.node_gets_set_total',
    'riak.node_gets_map',
    'riak.node_gets_map_total',
    'riak.node_puts_counter',
    'riak.node_puts_counter_total',
    'riak.node_puts_set',
    'riak.node_puts_set_total',
    'riak.node_puts_map',
    'riak.node_puts_map_total',
    'riak.object_merge',
    'riak.object_merge_total',
    'riak.object_counter_merge',
    'riak.object_counter_merge_total',
    'riak.object_set_merge',
    'riak.object_set_merge_total',
    'riak.object_map_merge',
    'riak.object_map_merge_total',
    'riak.pbc_active',
    'riak.pbc_connects',
    'riak.pbc_connects_total',
    'riak.read_repairs',
    'riak.read_repairs_total',
    'riak.skipped_read_repairs',
    'riak.skipped_read_repairs_total',
    'riak.read_repairs_counter',
    'riak.read_repairs_counter_total',
    'riak.read_repairs_set',
    'riak.read_repairs_set_total',
    'riak.read_repairs_map',
    'riak.read_repairs_map_total',
    'riak.node_get_fsm_active',
    'riak.node_get_fsm_active_60s',
    'riak.node_get_fsm_in_rate',
    'riak.node_get_fsm_out_rate',
    'riak.node_get_fsm_rejected',
    'riak.node_get_fsm_rejected_60s',
    'riak.node_get_fsm_rejected_total',
    'riak.node_get_fsm_errors',
    'riak.node_get_fsm_errors_total',
    'riak.node_put_fsm_active',
    'riak.node_put_fsm_active_60s',
    'riak.node_put_fsm_in_rate',
    'riak.node_put_fsm_out_rate',
    'riak.node_put_fsm_rejected',
    'riak.node_put_fsm_rejected_60s',
    'riak.node_put_fsm_rejected_total',
    'riak.riak_kv_vnodes_running',
    'riak.vnode_gets',
    'riak.vnode_gets_total',
    'riak.vnode_puts',
    'riak.vnode_puts_total',
    'riak.vnode_counter_update',
    'riak.vnode_counter_update_total',
    'riak.vnode_set_update',
    'riak.vnode_set_update_total',
    'riak.vnode_map_update',
    'riak.vnode_map_update_total',
    'riak.vnode_index_deletes',
    'riak.vnode_index_deletes_postings',
    'riak.vnode_index_deletes_postings_total',
    'riak.vnode_index_deletes_total',
    'riak.vnode_index_reads',
    'riak.vnode_index_reads_total',
    'riak.vnode_index_refreshes',
    'riak.vnode_index_refreshes_total',
    'riak.vnode_index_writes',
    'riak.vnode_index_writes_postings',
    'riak.vnode_index_writes_postings_total',
    'riak.vnode_index_writes_total',
    'riak.dropped_vnode_requests_total',
    'riak.list_fsm_active',
    'riak.list_fsm_create',
    'riak.list_fsm_create_total',
    'riak.list_fsm_create_error',
    'riak.list_fsm_create_error_total',
    'riak.index_fsm_active',
    'riak.index_fsm_create',
    'riak.index_fsm_create_error',
    'riak.riak_pipe_vnodes_running',
    'riak.executing_mappers',
    'riak.pipeline_active',
    'riak.pipeline_create_count',
    'riak.pipeline_create_error_count',
    'riak.pipeline_create_error_one',
    'riak.pipeline_create_one',
    'riak.rings_reconciled',
    'riak.rings_reconciled_total',
    'riak.converge_delay_last',
    'riak.converge_delay_max',
    'riak.converge_delay_mean',
    'riak.converge_delay_min',
    'riak.rebalance_delay_last',
    'riak.rebalance_delay_max',
    'riak.rebalance_delay_mean',
    'riak.rebalance_delay_min',
    'riak.rejected_handoffs',
    'riak.handoff_timeouts',
    'riak.coord_redirs_total',
    'riak.gossip_received',
    'riak.ignored_gossip_total',
    'riak.mem_allocated',
    'riak.mem_total',
    'riak.memory_atom',
    'riak.memory_atom_used',
    'riak.memory_binary',
    'riak.memory_code',
    'riak.memory_ets',
    'riak.memory_processes',
    'riak.memory_processes_used',
    'riak.memory_system',
    'riak.memory_total',
    'riak.sys_monitor_count',
    'riak.sys_port_count',
    'riak.sys_process_count',
    'riak.late_put_fsm_coordinator_ack',
    'riak.postcommit_fail',
    'riak.precommit_fail',
    'riak.leveldb_read_block_error',
]

CHECK_GAUGES_STATS = [
    'riak.node_get_fsm_counter_time_mean',
    'riak.node_get_fsm_counter_time_median',
    'riak.node_get_fsm_counter_time_95',
    'riak.node_get_fsm_counter_time_99',
    'riak.node_get_fsm_counter_time_100',
    'riak.node_put_fsm_counter_time_mean',
    'riak.node_put_fsm_counter_time_median',
    'riak.node_put_fsm_counter_time_95',
    'riak.node_put_fsm_counter_time_99',
    'riak.node_put_fsm_counter_time_100',
    'riak.node_get_fsm_set_time_mean',
    'riak.node_get_fsm_set_time_median',
    'riak.node_get_fsm_set_time_95',
    'riak.node_get_fsm_set_time_99',
    'riak.node_get_fsm_set_time_100',
    'riak.node_put_fsm_set_time_mean',
    'riak.node_put_fsm_set_time_median',
    'riak.node_put_fsm_set_time_95',
    'riak.node_put_fsm_set_time_99',
    'riak.node_put_fsm_set_time_100',
    'riak.node_get_fsm_map_time_mean',
    'riak.node_get_fsm_map_time_median',
    'riak.node_get_fsm_map_time_95',
    'riak.node_get_fsm_map_time_99',
    'riak.node_get_fsm_map_time_100',
    'riak.node_put_fsm_map_time_mean',
    'riak.node_put_fsm_map_time_median',
    'riak.node_put_fsm_map_time_95',
    'riak.node_put_fsm_map_time_99',
    'riak.node_put_fsm_map_time_100',
    'riak.node_get_fsm_counter_objsize_mean',
    'riak.node_get_fsm_counter_objsize_median',
    'riak.node_get_fsm_counter_objsize_95',
    'riak.node_get_fsm_counter_objsize_99',
    'riak.node_get_fsm_counter_objsize_100',
    'riak.node_get_fsm_set_objsize_mean',
    'riak.node_get_fsm_set_objsize_median',
    'riak.node_get_fsm_set_objsize_95',
    'riak.node_get_fsm_set_objsize_99',
    'riak.node_get_fsm_set_objsize_100',
    'riak.node_get_fsm_map_objsize_mean',
    'riak.node_get_fsm_map_objsize_median',
    'riak.node_get_fsm_map_objsize_95',
    'riak.node_get_fsm_map_objsize_99',
    'riak.node_get_fsm_map_objsize_100',
    'riak.node_get_fsm_counter_siblings_mean',
    'riak.node_get_fsm_counter_siblings_median',
    'riak.node_get_fsm_counter_siblings_95',
    'riak.node_get_fsm_counter_siblings_99',
    'riak.node_get_fsm_counter_siblings_100',
    'riak.node_get_fsm_set_siblings_mean',
    'riak.node_get_fsm_set_siblings_median',
    'riak.node_get_fsm_set_siblings_95',
    'riak.node_get_fsm_set_siblings_99',
    'riak.node_get_fsm_set_siblings_100',
    'riak.node_get_fsm_map_siblings_mean',
    'riak.node_get_fsm_map_siblings_median',
    'riak.node_get_fsm_map_siblings_95',
    'riak.node_get_fsm_map_siblings_99',
    'riak.node_get_fsm_map_siblings_100',
    'riak.object_merge_time_mean',
    'riak.object_merge_time_median',
    'riak.object_merge_time_95',
    'riak.object_merge_time_99',
    'riak.object_merge_time_100',
    'riak.object_counter_merge_time_mean',
    'riak.object_counter_merge_time_median',
    'riak.object_counter_merge_time_95',
    'riak.object_counter_merge_time_99',
    'riak.object_counter_merge_time_100',
    'riak.object_set_merge_time_mean',
    'riak.object_set_merge_time_median',
    'riak.object_set_merge_time_95',
    'riak.object_set_merge_time_99',
    'riak.object_set_merge_time_100',
    'riak.object_map_merge_time_mean',
    'riak.object_map_merge_time_median',
    'riak.object_map_merge_time_95',
    'riak.object_map_merge_time_99',
    'riak.object_map_merge_time_100',
    'riak.counter_actor_counts_mean',
    'riak.counter_actor_counts_median',
    'riak.counter_actor_counts_95',
    'riak.counter_actor_counts_99',
    'riak.counter_actor_counts_100',
    'riak.set_actor_counts_mean',
    'riak.set_actor_counts_median',
    'riak.set_actor_counts_95',
    'riak.set_actor_counts_99',
    'riak.set_actor_counts_100',
    'riak.map_actor_counts_mean',
    'riak.map_actor_counts_median',
    'riak.map_actor_counts_95',
    'riak.map_actor_counts_99',
    'riak.map_actor_counts_100',
    'riak.vnode_get_fsm_time_mean',
    'riak.vnode_get_fsm_time_median',
    'riak.vnode_get_fsm_time_95',
    'riak.vnode_get_fsm_time_99',
    'riak.vnode_get_fsm_time_100',
    'riak.vnode_put_fsm_time_mean',
    'riak.vnode_put_fsm_time_median',
    'riak.vnode_put_fsm_time_95',
    'riak.vnode_put_fsm_time_99',
    'riak.vnode_put_fsm_time_100',
    'riak.vnode_counter_update_time_mean',
    'riak.vnode_counter_update_time_median',
    'riak.vnode_counter_update_time_95',
    'riak.vnode_counter_update_time_99',
    'riak.vnode_counter_update_time_100',
    'riak.vnode_set_update_time_mean',
    'riak.vnode_set_update_time_median',
    'riak.vnode_set_update_time_95',
    'riak.vnode_set_update_time_99',
    'riak.vnode_set_update_time_100',
    'riak.vnode_map_update_time_mean',
    'riak.vnode_map_update_time_median',
    'riak.vnode_map_update_time_95',
    'riak.vnode_map_update_time_99',
    'riak.vnode_map_update_time_100',
    'riak.node_get_fsm_time_95',
    'riak.node_get_fsm_time_99',
    'riak.node_get_fsm_time_100',
    'riak.node_get_fsm_time_mean',
    'riak.node_get_fsm_time_median',
    'riak.node_get_fsm_siblings_mean',
    'riak.node_get_fsm_siblings_median',
    'riak.node_get_fsm_siblings_95',
    'riak.node_get_fsm_siblings_99',
    'riak.node_get_fsm_siblings_100',
    'riak.node_get_fsm_objsize_95',
    'riak.node_get_fsm_objsize_99',
    'riak.node_get_fsm_objsize_100',
    'riak.node_get_fsm_objsize_mean',
    'riak.node_get_fsm_objsize_median',
    'riak.node_put_fsm_time_95',
    'riak.node_put_fsm_time_median',
    'riak.node_put_fsm_time_100',
    'riak.node_put_fsm_time_mean',
    'riak.node_put_fsm_time_99',
    'riak.riak_kv_vnodeq_mean',
    'riak.riak_kv_vnodeq_min',
    'riak.riak_kv_vnodeq_max',
    'riak.riak_kv_vnodeq_median',
    'riak.riak_kv_vnodeq_total',
    'riak.riak_pipe_vnodeq_mean',
    'riak.riak_pipe_vnodeq_min',
    'riak.riak_pipe_vnodeq_max',
    'riak.riak_pipe_vnodeq_median',
    'riak.riak_pipe_vnodeq_total',
]

GAUGE_OTHER = [
    'riak.coord_redirs',
]

# The below metrics for leveldb and read repair
# appear when they have no values, however they
# are displayed as "undefined". The search metrics
# do not appear if search is off.
CHECK_NOT_TESTED = [
    'riak.read_repairs_primary_notfound_one',
    'riak.read_repairs_primary_notfound_count',
    'riak.read_repairs_primary_outofdate_one',
    'riak.read_repairs_primary_outofdate_count',
    'riak.read_repairs_fallback_notfound_one',
    'riak.read_repairs_fallback_notfound_count',
    'riak.read_repairs_fallback_outofdate_one',
    'riak.read_repairs_fallback_outofdate_count',
    'riak.search_query_latency_mean',
    'riak.search_query_latency_min',
    'riak.search_query_latency_median',
    'riak.search_query_latency_95',
    'riak.search_query_latency_99',
    'riak.search_query_latency_999',
    'riak.search_query_latency_max',
    'riak.search_index_latency_mean',
    'riak.search_index_latency_min',
    'riak.search_index_latency_median',
    'riak.search_index_latency_95',
    'riak.search_index_latency_99',
    'riak.search_index_latency_999',
    'riak.search_index_latency_max',
    'riak.search_index_fail_one',
    'riak.search_index_fail_count',
    'riak.search_index_throughput_one',
    'riak.search_index_throughput_count',
    'riak.search_query_fail_one',
    'riak.search_query_fail_count',
    'riak.search_query_throughput_one',
    'riak.search_query_throughput_count',
]

SERVICE_CHECK_NAME = 'riak.can_connect'

HERE = os.path.dirname(os.path.abspath(__file__))

HOST = get_docker_hostname()
PORT = 18098
BASE_URL = "http://{0}:{1}".format(HOST, PORT)


@pytest.fixture(scope="session")
def spin_up_riak():
    env = os.environ
    env['RIAK_CONFIG'] = os.path.join(HERE, 'config')
    args = [
        "docker-compose",
        "-f", os.path.join(HERE, 'compose', 'riak.yaml')
    ]
    subprocess.check_call(args + ["up", "-d"], env=env)
    can_access = False
    for _ in xrange(0, 10):
        res = None
        try:
            res = requests.get("{0}/riak/bucket".format(BASE_URL))
            log.info("response: {0}".format(res))
            log.info("status code: {0}, text: {1}".format(res.status_code, res.text))
            res.raise_for_status
            can_access = True
            break
        except Exception as e:
            log.info("exception: {0}, response: {1}".format(e, res))
            time.sleep(5)
    if not can_access:
        raise Exception("Cannot access Riak")

    data = 'herzlich willkommen'
    headers = {"Content-Type": "text/plain"}
    for _ in xrange(0, 10):
        res = requests.post(
            "{0}/riak/bucket/german".format(BASE_URL),
            headers=headers,
            data=data)
        res.raise_for_status
        res = requests.get("{0}/riak/bucket/german".format(BASE_URL))
        res.raise_for_status

    # some stats require a bit of time before the test will capture them
    time.sleep(10)
    yield
    subprocess.check_call(args + ["down"], env=env)


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


def test_check(aggregator, spin_up_riak):
    riak_check = Riak(CHECK_NAME, {}, {})
    config = {
            "url": "{0}/stats".format(BASE_URL),
            "tags": ["my_tag"]
    }
    riak_check.check(config)
    riak_check.check(config)
    tags = ['my_tag']
    sc_tags = tags + ['url:' + config['url']]

    for gauge in CHECK_GAUGES + CHECK_GAUGES_STATS:
        aggregator.assert_metric(gauge, tags=tags, count=2)

    for sc in aggregator.service_checks(SERVICE_CHECK_NAME):
        assert sc.status == Riak.OK
        for tag in sc.tags:
            assert tag in sc_tags

    for gauge in GAUGE_OTHER:
        aggregator.assert_metric(gauge, count=1)

    aggregator.all_metrics_asserted()


def test_bad_config(aggregator, spin_up_riak):
    riak_check = Riak(CHECK_NAME, {}, {})
    with pytest.raises(socket.error):
        riak_check.check({"url": "http://localhost:5985"})

    sc_tags = ['url:http://localhost:5985']
    for sc in aggregator.service_checks(SERVICE_CHECK_NAME):
        assert sc.status == Riak.CRITICAL
        for tag in sc.tags:
            assert tag in sc_tags
