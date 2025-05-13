# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from unittest.mock import patch

import pytest

from datadog_checks.slurm import SlurmCheck
from datadog_checks.slurm.constants import SACCT_PARAMS

from .common import (
    DEFAULT_SINFO_PATH,
    SACCT_MAP,
    SCONTROL_MAP,
    SDIAG_MAP,
    SINFO_1_F,
    SINFO_1_T,
    SINFO_2_F,
    SINFO_2_T,
    SINFO_3_F,
    SINFO_3_T,
    SINFO_MAP,
    SLURM_VERSION,
    SQUEUE_MAP,
    SSHARE_MAP,
    mock_output,
)


@pytest.mark.parametrize(
    "collection_level, gpu_stats, expected_params",
    [
        (1, False, DEFAULT_SINFO_PATH + SINFO_1_F),
        (2, False, DEFAULT_SINFO_PATH + SINFO_2_F),
        (3, False, DEFAULT_SINFO_PATH + SINFO_3_F),
        (1, True, DEFAULT_SINFO_PATH + SINFO_1_T),
        (2, True, DEFAULT_SINFO_PATH + SINFO_2_T),
        (3, True, DEFAULT_SINFO_PATH + SINFO_3_T),
    ],
)
def test_sinfo_command_params(collection_level, gpu_stats, expected_params, instance):
    # Mock the instance configuration
    instance['collect_sinfo_stats'] = True
    instance['sinfo_collection_level'] = collection_level
    instance['collect_gpu_stats'] = gpu_stats

    check = SlurmCheck('slurm', {}, [instance])

    if collection_level > 1:
        assert check.sinfo_node_cmd == expected_params
    else:
        assert check.sinfo_partition_cmd == expected_params


def test_acct_command_params(instance):
    # Mock the instance configuration
    instance['collect_sacct_stats'] = True

    check = SlurmCheck('slurm', {}, [instance])
    base_cmd = ['/usr/bin/sacct'] + SACCT_PARAMS

    # Test to ensure that the sacct is being constructed correctly
    loops = [0, 1, 2]
    for loop in loops:
        if loop > 0:
            time.sleep(loop)
        check._update_sacct_params()
        expected_cmd = base_cmd + ([f'--starttime=now-{loop}seconds'] if loop > 0 else [])
        assert check.sacct_cmd == expected_cmd


@patch('datadog_checks.slurm.check.get_subprocess_output')
def test_sinfo_processing(mock_get_subprocess_output, instance, aggregator):
    instance['collect_sinfo_stats'] = True
    check = SlurmCheck('slurm', {}, [instance])
    # sinfo has 3 subprocess calls. It collects metadata, partition and node data. So I'm mocking all of them.
    mock_output_metadata = ("", "", 1)
    mock_output_partition = (mock_output('sinfo_partition.txt'), "", 0)
    mock_output_main = (mock_output('sinfo.txt'), "", 0)
    mock_get_subprocess_output.side_effect = [mock_output_metadata, mock_output_partition, mock_output_main]
    check.check(None)
    for metric in SINFO_MAP['metrics']:
        aggregator.assert_metric(name=metric['name'], value=metric['value'], tags=metric['tags'])
    aggregator.assert_all_metrics_covered()


@patch('datadog_checks.slurm.check.get_subprocess_output')
def test_squeue_processing(mock_get_subprocess_output, instance, aggregator):
    instance['collect_squeue_stats'] = True
    check = SlurmCheck('slurm', {}, [instance])
    mock_output_main = (mock_output('squeue.txt'), "", 0)
    mock_get_subprocess_output.side_effect = [mock_output_main]
    check.check(None)
    for metric in SQUEUE_MAP['metrics']:
        aggregator.assert_metric(name=metric['name'], value=metric['value'], tags=metric['tags'])
    aggregator.assert_all_metrics_covered()


@patch('datadog_checks.slurm.check.get_subprocess_output')
def test_sacct_processing(mock_get_subprocess_output, instance, aggregator):
    instance['collect_sacct_stats'] = True
    check = SlurmCheck('slurm', {}, [instance])
    mock_output_main = (mock_output('sacct.txt'), "", 0)
    mock_get_subprocess_output.side_effect = [mock_output_main]
    # This one doesn't collect anything on the first run. It only collects on the second run.
    check.check(None)
    check.check(None)
    for metric in SACCT_MAP['metrics']:
        aggregator.assert_metric(name=metric['name'], value=metric['value'], tags=metric['tags'])
    aggregator.assert_all_metrics_covered()


@patch('datadog_checks.slurm.check.get_subprocess_output')
def test_sshare_processing(mock_get_subprocess_output, instance, aggregator):
    instance['collect_sshare_stats'] = True
    check = SlurmCheck('slurm', {}, [instance])
    mock_output_main = (mock_output('sshare.txt'), "", 0)
    mock_get_subprocess_output.side_effect = [mock_output_main]
    check.check(None)
    for metric in SSHARE_MAP['metrics']:
        aggregator.assert_metric(name=metric['name'], value=metric['value'], tags=metric['tags'])
    aggregator.assert_all_metrics_covered()


@patch('datadog_checks.slurm.check.get_subprocess_output')
def test_sdiag_processing(mock_get_subprocess_output, instance, aggregator):
    instance['collect_sdiag_stats'] = True
    check = SlurmCheck('slurm', {}, [instance])
    mock_output_main = (mock_output('sdiag.txt'), "", 0)
    mock_get_subprocess_output.side_effect = [mock_output_main]
    from unittest.mock import patch as patch_time

    # Patch time.time only for sdiag to make the test deterministic
    with patch_time('datadog_checks.slurm.check.time') as mock_time:
        # The epoch in sdiag.txt is 1726207912, mocking current time to 1726208912 (diff = 1000)
        mock_time.time.return_value = 1726208912
        check.check(None)
    for metric in SDIAG_MAP['metrics']:
        aggregator.assert_metric(name=metric['name'], value=metric['value'], tags=metric['tags'])
    aggregator.assert_all_metrics_covered()


@patch('datadog_checks.slurm.check.get_subprocess_output')
def test_scontrol_processing(mock_get_subprocess_output, instance, aggregator):
    instance['collect_scontrol_stats'] = True
    check = SlurmCheck('slurm', {}, [instance])
    base_cmd = ['/usr/bin/scontrol']
    assert check.scontrol_cmd[:-1] == base_cmd
    mock_output_main = (mock_output('scontrol.txt'), "", 0)
    mock_output_node = ("c1", "", 0)
    mock_output_squeue = (mock_output('scontrol_squeue.txt'), "", 0)
    mock_output_squeue2 = (mock_output('scontrol_squeue2.txt'), "", 0)
    # The below essentially mocks the return of all the function calls in the scontrol method. The first call mocks
    # the scontrol command output. The second mocks the hostname check. The third and fourth mock the squeue command
    # output when the 2 lines of scontrol are iterated over for metric submission.
    mock_get_subprocess_output.side_effect = [
        mock_output_main,
        mock_output_node,
        mock_output_squeue,
        mock_output_squeue2,
    ]
    check.check(None)
    for metric in SCONTROL_MAP['metrics']:
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


@patch('datadog_checks.slurm.check.get_subprocess_output')
def test_enrich_scontrol_tags_error(mock_get_subprocess_output, instance, caplog):
    # Test enrich_scontrol_tags error
    instance['collect_scontrol_stats'] = True
    check = SlurmCheck('slurm', {}, [instance])

    # Test error case in squeue command
    mock_get_subprocess_output.return_value = (None, "Squeue command failed", 1)
    result = check._enrich_scontrol_tags("123")
    assert result == []
    assert "Error fetching squeue details for job 123: Squeue command failed" in caplog.text

    # Test exception case
    mock_get_subprocess_output.side_effect = Exception("Test exception")
    result = check._enrich_scontrol_tags("123")
    assert result == []
    assert "Error fetching squeue details for job 123: Test exception" in caplog.text


@patch('datadog_checks.slurm.check.get_subprocess_output')
def test_enrich_scontrol_tags_unexpected_parts(mock_get_subprocess_output, instance, caplog):
    instance['collect_scontrol_stats'] = True
    check = SlurmCheck('slurm', {}, [instance])

    # Test case where squeue returns more than 3 parts
    mock_get_subprocess_output.return_value = ("root RUNNING test_job extra_field", "", 0)
    result = check._enrich_scontrol_tags("123")
    assert result == []

    # Test case where squeue returns 2 parts
    mock_get_subprocess_output.return_value = ("root RUNNING", "", 0)
    result = check._enrich_scontrol_tags("123")
    assert result == []
