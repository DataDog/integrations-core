# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import patch

import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics # noqa: F401
from datadog_checks.slurm import SlurmCheck

from .common import SACCT_MAP, SDIAG_MAP, SINFO_MAP, SLURM_VERSION, SQUEUE_MAP, SSHARE_MAP, mock_output


@pytest.mark.parametrize(
    "expected_metrics, binary",
    [
        (SINFO_MAP, 'sinfo'),
        (SQUEUE_MAP, 'squeue'),
        (SACCT_MAP, 'sacct'),
        (SSHARE_MAP, 'sshare'),
        (SDIAG_MAP, 'sdiag'),
    ],
    ids=['sinfo with full params', 'squeue output', 'sacct output', 'sshare output', 'sdiag output'],
)
@patch('datadog_checks.slurm.check.get_subprocess_output')
def test_slurm_binary_processing(mock_get_subprocess_output, instance, aggregator, expected_metrics, binary):
    instance[f'collect_{binary}_stats'] = True

    # Metadata collection happens before the main collection so I'm mocking a failed call for it.
    mock_output_main = (mock_output(f'{binary}.txt'), "", 0)

    if binary == 'sinfo':
        # sinfo has 3 subprocess calls. It collects metadata, partition and node data. So I'm mocking all of them.
        mock_output_metadata = ("", "", 1)
        mock_output_partition = (mock_output('sinfo_partition.txt'), "", 0)
        mock_get_subprocess_output.side_effect = [mock_output_metadata, mock_output_partition, mock_output_main]
    else:
        mock_get_subprocess_output.side_effect = [mock_output_main]

    check = SlurmCheck('slurm', {}, [instance])

    check.check(None)
    if binary == 'sacct':
        # This one doesn't collect anything on the first run. It only collects on the second run.
        check.check(None)

    for metric in expected_metrics['metrics']:
        aggregator.assert_metric(name=metric['name'], value=metric['value'], tags=metric['tags'])

    aggregator.assert_all_metrics_covered()


@patch('datadog_checks.slurm.check.get_subprocess_output')
def test_metadata(mock_get_subprocess_out, instance, datadog_agent, dd_run_check):
    instance['collect_sinfo_stats'] = True
    instance['sinfo_collection_level'] = 1
    check = SlurmCheck('slurm', {}, [instance])
    check.check_id = 'test:123'

    mock_sinfo_output = mock_output('sinfo_version.txt')

    # First return for the metadata, the second one is for the sinfo partition
    # metric collection. But we don't care about that here.
    mock_get_subprocess_out.side_effect = [
        (mock_sinfo_output, "", 0),
        ("", "", 1),
    ]

    dd_run_check(check)

    raw_version = SLURM_VERSION
    major, minor, mod = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'slurm',
        'version.major': major,
        'version.minor': minor,
        'version.mod': mod,
        'version.raw': raw_version,
    }
    datadog_agent.assert_metadata('test:123', version_metadata)


