# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


# [object, instance of counter, counter name, metric name, metric type]
#
# This set is (mostly) from the Microsoft recommended counters to monitor Hyper-V:
# https://docs.microsoft.com/en-us/windows-server/administration/performance-tuning/role/hyper-v-server
# https://blogs.technet.microsoft.com/neales/2016/10/24/hyper-v-performance-cpu
# TODO: Investigate additional recommended counters from:
# https://blogs.technet.microsoft.com/chrisavis/2013/03/25/performance-management-monitoring-cpu-resources
DEFAULT_COUNTERS = [
    # Memory
    [
        'Hyper-V Dynamic Memory Balancer',
        None,
        'Available Memory',
        'hyperv.dynamic_memory_balancer.available_memory',
        'gauge',
    ],
    [
        'Hyper-V Dynamic Memory Balancer',
        None,
        'Average Pressure',
        'hyperv.dynamic_memory_balancer.average_pressure',
        'gauge',
    ],
    # Network
    ['Hyper-V Virtual Network Adapter', None, 'Bytes/sec', 'hyperv.virtual_network_adapter.bytes_per_sec', 'gauge'],
    # Processor
    [
        'Hyper-V Hypervisor Logical Processor',
        None,
        '% Guest Run Time',
        'hyperv.hypervisor_logical_processor.guest_run_time',
        'gauge',
    ],
    [
        'Hyper-V Hypervisor Logical Processor',
        None,
        '% Hypervisor Run Time',
        'hyperv.hypervisor_logical_processor.hypervisor_run_time',
        'gauge',
    ],
    [
        'Hyper-V Hypervisor Logical Processor',
        None,
        '% Idle Time',
        'hyperv.hypervisor_logical_processor.idle_time',
        'gauge',
    ],
    [
        'Hyper-V Hypervisor Logical Processor',
        None,
        '% Total Run Time',
        'hyperv.hypervisor_logical_processor.total_run_time',
        'gauge',
    ],
    [
        'Hyper-V Hypervisor Logical Processor',
        None,
        'Context Switches/sec',
        'hyperv.hypervisor_logical_processor.context_switches_per_sec',
        'gauge',
    ],
    [
        'Hyper-V Hypervisor Root Virtual Processor',
        None,
        '% Guest Run Time',
        'hyperv.hypervisor_root_virtual_processor.guest_run_time',
        'gauge',
    ],
    [
        'Hyper-V Hypervisor Root Virtual Processor',
        None,
        '% Hypervisor Run Time',
        'hyperv.hypervisor_root_virtual_processor.hypervisor_run_time',
        'gauge',
    ],
    [
        'Hyper-V Hypervisor Root Virtual Processor',
        None,
        '% Total Run Time',
        'hyperv.hypervisor_root_virtual_processor.total_run_time',
        'gauge',
    ],
    [
        'Hyper-V Hypervisor Virtual Processor',
        None,
        '% Guest Run Time',
        'hyperv.hypervisor_virtual_processor.guest_run_time',
        'gauge',
    ],
    [
        'Hyper-V Hypervisor Virtual Processor',
        None,
        '% Hypervisor Run Time',
        'hyperv.hypervisor_virtual_processor.hypervisor_run_time',
        'gauge',
    ],
    [
        'Hyper-V Hypervisor Virtual Processor',
        None,
        '% Total Run Time',
        'hyperv.hypervisor_virtual_processor.total_run_time',
        'gauge',
    ],
    # Storage
    [
        'Hyper-V VM Vid Partition',
        None,
        'Physical Pages Allocated',
        'hyperv.vm_vid_partition.physical_pages_allocated',
        'gauge',
    ],
    [
        'Hyper-V VM Vid Partition',
        None,
        'Remote Physical Pages',
        'hyperv.vm_vid_partition.remote_physical_pages',
        'gauge',
    ],
]

METRICS_CONFIG = {
    'Hyper-V Dynamic Memory Balancer': {
        'name': 'dynamic_memory_balancer',
        'counters': [{'Available Memory': 'available_memory', 'Average Pressure': 'average_pressure'}],
    },
    'Hyper-V Virtual Network Adapter': {
        'name': 'virtual_network_adapter',
        'counters': [{'Bytes/sec': 'bytes_per_sec'}],
    },
    'Hyper-V Hypervisor Logical Processor': {
        'name': 'hypervisor_logical_processor',
        'counters': [
            {
                '% Guest Run Time': 'guest_run_time',
                '% Hypervisor Run Time': 'hypervisor_run_time',
                '% Idle Time': 'idle_time',
                '% Total Run Time': 'total_run_time',
                'Context Switches/sec': 'context_switches_per_sec',
            }
        ],
    },
    'Hyper-V Hypervisor Root Virtual Processor': {
        'name': 'hypervisor_root_virtual_processor',
        'counters': [
            {
                '% Guest Run Time': 'guest_run_time',
                '% Hypervisor Run Time': 'hypervisor_run_time',
                '% Total Run Time': 'total_run_time',
            }
        ],
    },
    'Hyper-V Hypervisor Virtual Processor': {
        'name': 'hypervisor_virtual_processor',
        'counters': [
            {
                '% Guest Run Time': 'guest_run_time',
                '% Hypervisor Run Time': 'hypervisor_run_time',
                '% Total Run Time': 'total_run_time',
            }
        ],
    },
    'Hyper-V VM Vid Partition': {
        'name': 'vm_vid_partition',
        'counters': [
            {
                'Physical Pages Allocated': 'physical_pages_allocated',
                'Remote Physical Pages': 'remote_physical_pages',
            }
        ],
    },
}
