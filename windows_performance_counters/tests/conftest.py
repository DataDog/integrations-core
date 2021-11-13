# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.fixture(scope='session')
def dd_environment():
    instance = {
        'namespace': 'test',
        'metrics': {
            'Processor': {
                'name': 'cpu',
                'tag_name': 'thread',
                'instance_counts': {
                    'total': 'num_cpu_threads.total',
                    'monitored': 'num_cpu_threads.monitored',
                    'unique': 'num_cpu_threads.unique',
                },
                'counters': [{'Interrupts/sec': 'interrupts.ps', '% User Time': {'metric_name': 'core.user_time'}}],
            }
        },
        'server_tag': 'machine',
        'tags': ['foo:bar', 'bar:baz'],
    }
    e2e_metadata = {'docker_platform': 'windows'}
    yield instance, e2e_metadata
