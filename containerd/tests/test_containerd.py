# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import pytest
import mock

# 3p

# project
from datadog_checks.containerd import ContainerdCheck

instance = {
    'prometheus_url': 'http://localhost:1338/v1/metrics',
}

# Constants
CHECK_NAME = 'containerd'
NAMESPACE = 'containerd'


@pytest.fixture()
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture()
def mock_containerd_out():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'containerd-out.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    containerd_out = mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200,
            iter_lines=lambda **kwargs: text_data.split("\n"),
            headers={'Content-Type': "text/plain"}
        )
    )
    yield containerd_out.start()
    containerd_out.stop()


def test_check_containerd(aggregator, mock_containerd_out):
    """
    Testing output from containerd.
    """

    c = ContainerdCheck(CHECK_NAME, None, {}, [instance])
    c.check(instance)
    aggregator.assert_metric(NAMESPACE + '.blkio_io_svc_bytes_recursive')
    aggregator.assert_metric(NAMESPACE + '.blkio_io_svc_recursive_total')
    aggregator.assert_metric(NAMESPACE + '.cpu_kernel')
    aggregator.assert_metric(NAMESPACE + '.cpu_throttled_time')
    aggregator.assert_metric(NAMESPACE + '.cpu_total')
    aggregator.assert_metric(NAMESPACE + '.cpu_user')
    aggregator.assert_metric(NAMESPACE + '.hugetlb_failcnt_total')
    aggregator.assert_metric(NAMESPACE + '.hugetlb_max')
    aggregator.assert_metric(NAMESPACE + '.hugetlb_usage')
    aggregator.assert_metric(NAMESPACE + '.mem_active_anon')
    aggregator.assert_metric(NAMESPACE + '.mem_active_file')
    aggregator.assert_metric(NAMESPACE + '.mem_cache')
    aggregator.assert_metric(NAMESPACE + '.mem_dirty')
    aggregator.assert_metric(NAMESPACE + '.mem_hierarchical_memory_limit')
    aggregator.assert_metric(NAMESPACE + '.mem_hierarchical_memsw_limit')
    aggregator.assert_metric(NAMESPACE + '.mem_inactive_anon')
    aggregator.assert_metric(NAMESPACE + '.mem_inactive_file')
    aggregator.assert_metric(NAMESPACE + '.mem_kernel_failcnt_total')
    aggregator.assert_metric(NAMESPACE + '.mem_kernel_limit')
    aggregator.assert_metric(NAMESPACE + '.mem_kernel_max')
    aggregator.assert_metric(NAMESPACE + '.mem_kernel_usage')
    aggregator.assert_metric(NAMESPACE + '.mem_kerneltcp_failcnt_total')
    aggregator.assert_metric(NAMESPACE + '.mem_kerneltcp_limit')
    aggregator.assert_metric(NAMESPACE + '.mem_kerneltcp_max')
    aggregator.assert_metric(NAMESPACE + '.mem_kerneltcp_usage')
    aggregator.assert_metric(NAMESPACE + '.mem_mapped_file')
    aggregator.assert_metric(NAMESPACE + '.mem_oom_total')
    aggregator.assert_metric(NAMESPACE + '.mem_pgfault')
    aggregator.assert_metric(NAMESPACE + '.mem_pgmajfault')
    aggregator.assert_metric(NAMESPACE + '.mem_pgpgin')
    aggregator.assert_metric(NAMESPACE + '.mem_pgpgout')
    aggregator.assert_metric(NAMESPACE + '.mem_rss')
    aggregator.assert_metric(NAMESPACE + '.mem_rss_huge')
    aggregator.assert_metric(NAMESPACE + '.mem_swap_failcnt_total')
    aggregator.assert_metric(NAMESPACE + '.mem_swap_limit')
    aggregator.assert_metric(NAMESPACE + '.mem_swap_max')
    aggregator.assert_metric(NAMESPACE + '.mem_swap_usage')
    aggregator.assert_metric(NAMESPACE + '.mem_total_active_anon')
    aggregator.assert_metric(NAMESPACE + '.mem_total_active_file')
    aggregator.assert_metric(NAMESPACE + '.mem_total_cache')
    aggregator.assert_metric(NAMESPACE + '.mem_total_dirty')
    aggregator.assert_metric(NAMESPACE + '.mem_total_inactive_anon')
    aggregator.assert_metric(NAMESPACE + '.mem_total_inactive_file')
    aggregator.assert_metric(NAMESPACE + '.mem_total_mapped_file')
    aggregator.assert_metric(NAMESPACE + '.mem_total_pgfault')
    aggregator.assert_metric(NAMESPACE + '.mem_total_pgmajfault')
    aggregator.assert_metric(NAMESPACE + '.mem_total_pgpgin')
    aggregator.assert_metric(NAMESPACE + '.mem_total_pgpgout')
    aggregator.assert_metric(NAMESPACE + '.mem_total_rss')
    aggregator.assert_metric(NAMESPACE + '.mem_total_rss_huge')
    aggregator.assert_metric(NAMESPACE + '.mem_total_unevictable')
    aggregator.assert_metric(NAMESPACE + '.mem_total_writeback')
    aggregator.assert_metric(NAMESPACE + '.mem_unevictable')
    aggregator.assert_metric(NAMESPACE + '.mem_usage_failcnt_total')
    aggregator.assert_metric(NAMESPACE + '.mem_usage_limit')
    aggregator.assert_metric(NAMESPACE + '.mem_usage_max')
    aggregator.assert_metric(NAMESPACE + '.mem_usage')
    aggregator.assert_metric(NAMESPACE + '.mem_writeback')
    aggregator.assert_metric(NAMESPACE + '.per_cpu')
    aggregator.assert_metric(NAMESPACE + '.pids_current')
    aggregator.assert_metric(NAMESPACE + '.pids_limit')
    aggregator.assert_metric(NAMESPACE + '.go.goroutines')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_alloc')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_alloc_bytes_total')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_buck_hash_sys')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_frees_total')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_gc_cpu_fraction')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_gc_sys')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_heap_alloc')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_heap_idle')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_heap_inuse')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_heap_objects')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_heap_released')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_heap_sys')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_last_gc_time_seconds')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_lookups_total')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_mallocs_total')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_mcache_inuse')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_mcache_sys')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_mspan_inuse')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_mspan_sys')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_next_gc')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_other_sys')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_stack_inuse')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_stack_sys')
    aggregator.assert_metric(NAMESPACE + '.go.memstats_sys')
    aggregator.assert_metric(NAMESPACE + '.go.threads')
    aggregator.assert_metric(NAMESPACE + '.grpc.server_msg_received_total')
    aggregator.assert_metric(NAMESPACE + '.grpc.server_handled_total')
    aggregator.assert_metric(NAMESPACE + '.grpc.server_msg_sent_total')
    aggregator.assert_metric(NAMESPACE + '.grpc.server_started_total')
    aggregator.assert_metric(NAMESPACE + '.http.requests_total')
    aggregator.assert_metric(NAMESPACE + '.process.cpu_seconds_total')
    aggregator.assert_metric(NAMESPACE + '.process.max_fds')
    aggregator.assert_metric(NAMESPACE + '.process.open_fds')
    aggregator.assert_metric(NAMESPACE + '.process.resident_memory')
    aggregator.assert_metric(NAMESPACE + '.process.start_time_seconds')
