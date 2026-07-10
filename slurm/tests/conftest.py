# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from unittest.mock import patch

import pytest


@pytest.fixture
def no_metadata():
    # Metadata collection shells out to `sinfo --version`; stub it so per-command tests own the
    # get_subprocess_output side_effect sequence. Metadata itself is covered by test_metadata.
    with patch('datadog_checks.slurm.check.SlurmCheck.collect_metadata'):
        yield


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
        'collect_scontrol_stats': False,
    }


@pytest.fixture
def caplog(caplog):
    caplog.set_level(logging.DEBUG)
    return caplog
