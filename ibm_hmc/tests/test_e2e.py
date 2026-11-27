# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.dev.utils import get_metadata_metrics


def test_e2e(dd_agent_check, e2e_instance):
    aggregator = dd_agent_check(e2e_instance, rate=True)

    aggregator.assert_metric('ibm_hmc.can_connect', value=1)
    # Managed system metrics, one series per LPAR and per shared processor pool
    lpar_a_tags = [
        'hmc-instance:127.0.0.1-8022',
        'server:e2eServer',
        'lpar_name:lparA',
        'curr_sharing_mode:cap',
        'mem_mode:ded',
    ]
    aggregator.assert_metric('ibm_hmc.lpar.curr_proc_units', value=0.5, tags=lpar_a_tags)
    aggregator.assert_metric(
        'ibm_hmc.lpar.curr_proc_units',
        value=2.0,
        tags=[
            'hmc-instance:127.0.0.1-8022',
            'server:e2eServer',
            'lpar_name:lparB',
            'curr_sharing_mode:uncap',
            'mem_mode:shared',
        ],
    )
    aggregator.assert_metric('ibm_hmc.lpar.curr_mem', value=2048, tags=lpar_a_tags)
    aggregator.assert_metric(
        'ibm_hmc.pool.curr_avail_pool_proc_units', value=1.10, tags=['hmc-instance:127.0.0.1-8022', 'server:e2eServer']
    )
    aggregator.assert_metric(
        'ibm_hmc.mempool.curr_pool_mem', value=24576, tags=['hmc-instance:127.0.0.1-8022', 'server:e2eServer']
    )
    aggregator.assert_metric(
        'ibm_hmc.sys.curr_avail_sys_mem', value=37376, tags=['hmc-instance:127.0.0.1-8022', 'server:e2eServer']
    )
    # The cycle metrics are cumulative counters, submitted as monotonic counts
    aggregator.assert_metric('ibm_hmc.lpar.entitled_cycles', tags=lpar_a_tags)

    # HMC appliance metrics: real /proc/meminfo of the container and the fake monhmc
    aggregator.assert_metric('ibm_hmc.system.memory.memtotal')
    aggregator.assert_metric('ibm_hmc.system.memory.swap.total', value=2040244, tags=['hmc-instance:127.0.0.1-8022'])

    # Everything submitted is declared in metadata.csv with the right type
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
