# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
CHECK_NAME = 'process'

PROCESS_METRIC = [
    'system.processes.involuntary_ctx_switches',
    'system.processes.ioread_bytes',
    'system.processes.ioread_count',
    'system.processes.iowrite_bytes',
    'system.processes.iowrite_count',
    'system.processes.mem.pct',
    'system.processes.mem.real',
    'system.processes.mem.rss',
    'system.processes.mem.vms',
    'system.processes.number',
    'system.processes.open_file_descriptors',
    'system.processes.threads',
    'system.processes.voluntary_ctx_switches',
    'system.processes.run_time.avg',
    'system.processes.run_time.max',
    'system.processes.run_time.min',
]

PAGEFAULT_STAT = [
    'minor_faults',
    'children_minor_faults',
    'major_faults',
    'children_major_faults'
]

UNIX_TO_WINDOWS_MAP = {
    'system.processes.open_file_descriptors': 'system.processes.open_handles'
}


def get_config_stubs():
    return [
        {
            'instance': {
                'name': 'test_0',
                # index in the array for our find_pids mock
                'search_string': ['test_0'],
                'thresholds': {
                    'critical': [2, 4],
                    'warning': [1, 5]
                }
            },
            'mocked_processes': set()
        },
        {
            'instance': {
                'name': 'test_1',
                # index in the array for our find_pids mock
                'search_string': ['test_1'],
                'thresholds': {
                    'critical': [1, 5],
                    'warning': [2, 4]
                }
            },
            'mocked_processes': set([1])
        },
        {
            'instance': {
                'name': 'test_2',
                # index in the array for our find_pids mock
                'search_string': ['test_2'],
                'thresholds': {
                    'critical': [2, 5],
                    'warning': [1, 4]
                }
            },
            'mocked_processes': set([22, 35])
        },
        {
            'instance': {
                'name': 'test_3',
                # index in the array for our find_pids mock
                'search_string': ['test_3'],
                'thresholds': {
                    'critical': [1, 4],
                    'warning': [2, 5]
                }
            },
            'mocked_processes': set([1, 5, 44, 901, 34])
        },
        {
            'instance': {
                'name': 'test_4',
                # index in the array for our find_pids mock
                'search_string': ['test_4'],
                'thresholds': {
                    'critical': [1, 4],
                    'warning': [2, 5]
                }
            },
            'mocked_processes': set([3, 7, 2, 9, 34, 72])
        },
        {
            'instance': {
                'name': 'test_tags',
                # index in the array for our find_pids mock
                'search_string': ['test_5'],
                'tags': ['onetag', 'env:prod']
            },
            'mocked_processes': set([2])
        },
        {
            'instance': {
                'name': 'test_badthresholds',
                # index in the array for our find_pids mock
                'search_string': ['test_6'],
                'thresholds': {
                    'test': 'test'
                }
            },
            'mocked_processes': set([89])
        },
        {
            'instance': {
                'name': 'test_7',
                # index in the array for our find_pids mock
                'search_string': ['test_7'],
                'thresholds': {
                    'critical': [2, 4],
                    'warning': [1, 5]
                }
            },
            'mocked_processes': set([1])
        },
        {
            'instance': {
                'name': 'test_8',
                'pid': 1,
            },
            'mocked_processes': set([1])
        },
        {
            'instance': {
                'name': 'test_9',
                'pid_file': 'process/test/ci/fixtures/test_pid_file',
            },
            'mocked_processes': set([1])
        }
    ]
