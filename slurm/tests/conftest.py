# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return {
        'sinfo_collection_level': 3,
        'gpu_stats': False,
        'collect_sinfo_stats': False,
        'collect_squeue_stats': False,
        'collect_sdiag_stats': False,
        'collect_sshare_stats': False,
        'collect_sacct_stats': False,
        'collect_gpu_stats': True,
    }
