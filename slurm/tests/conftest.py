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
        'gpu_stats': True,
        'collect_sinfo_stats': True,
        'collect_squeue_stats': True,
        'collect_sdiag_stats': True,
        'collect_sshare_stats': True,
        'collect_sacct_stats': True,
        'collect_gpu_stats': True,
    }
