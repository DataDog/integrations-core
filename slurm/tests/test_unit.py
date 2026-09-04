# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from unittest.mock import patch

import pytest

from datadog_checks.slurm import SlurmCheck
from datadog_checks.slurm.check import ProcessPidMatch
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
    SINFO_LEVEL_2_MAP,
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
    # sinfo has 4 subprocess calls now: metadata, partition_cluster, partition_info, and node data.
    # So I'm mocking all of them.
    mock_output_metadata = ("", "", 1)
    mock_output_partition_cluster = (mock_output('sinfo_partition_cluster.txt'), "", 0)
    mock_output_partition_info = (mock_output('sinfo_partition_info.txt'), "", 0)
    mock_output_main = (mock_output('sinfo.txt'), "", 0)
    mock_get_subprocess_output.side_effect = [
        mock_output_metadata,
        mock_output_partition_cluster,
        mock_output_partition_info,
        mock_output_main,
    ]
    check.check(None)
    for metric in SINFO_MAP['metrics']:
        aggregator.assert_metric(name=metric['name'], value=metric['value'], tags=metric['tags'])
    aggregator.assert_all_metrics_covered()


@patch('datadog_checks.slurm.check.get_subprocess_output')
def test_sinfo_level_2_processing(mock_get_subprocess_output, instance, aggregator, caplog):
    instance['collect_sinfo_stats'] = True
    instance['sinfo_collection_level'] = 2
    instance['collect_gpu_stats'] = False
    check = SlurmCheck('slurm', {}, [instance])
    # sinfo has 4 subprocess calls now: metadata, partition_cluster, partition_info, and node data.
    # So I'm mocking all of them.
    mock_output_metadata = ("", "", 1)
    mock_output_partition_cluster = (mock_output('sinfo_partition_cluster.txt'), "", 0)
    mock_output_partition_info = (mock_output('sinfo_partition_info.txt'), "", 0)
    mock_output_main = (mock_output('sinfo_collection_level_2.txt'), "", 0)
    mock_get_subprocess_output.side_effect = [
        mock_output_metadata,
        mock_output_partition_cluster,
        mock_output_partition_info,
        mock_output_main,
    ]

    with caplog.at_level('DEBUG'):
        check.check(None)
        assert "out of range for tag" not in caplog.text
        assert "out of range for metric" not in caplog.text

    for metric in SINFO_LEVEL_2_MAP['metrics']:
        aggregator.assert_metric(name=metric['name'], value=metric['value'], tags=metric['tags'])


@patch('datadog_checks.slurm.check.get_subprocess_output')
def test_sinfo_error_logs(mock_get_subprocess_output, instance, caplog):
    instance['collect_sinfo_stats'] = True
    instance['sinfo_collection_level'] = 3
    instance['collect_gpu_stats'] = True
    check = SlurmCheck('slurm', {}, [instance])

    # Use the real fixture file for the main sinfo output
    sinfo_output = mock_output('sinfo_collection_level_2.txt')

    # sinfo has 4 subprocess calls now: metadata, partition_cluster, partition_info, and node data.
    # So I'm mocking all of them.
    mock_get_subprocess_output.side_effect = [
        ("", "", 1),
        ("", "", 1),
        ("", "", 1),
        (sinfo_output, "", 0),
    ]

    with caplog.at_level('DEBUG'):
        check.check(None)
        assert "out of range for tag" in caplog.text
        assert "out of range for metric" in caplog.text


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
def test_scontrol_processing_resolves_host_pid(mock_get_subprocess_output, instance, aggregator, monkeypatch, tmp_path):
    instance['collect_scontrol_stats'] = True
    instance['resolve_scontrol_host_pids'] = True
    check = SlurmCheck('slurm', {}, [instance])
    host_proc = tmp_path / "proc"
    host_process = host_proc / "12345"
    other_process = host_proc / "999"
    host_process.mkdir(parents=True)
    other_process.mkdir()
    (host_process / "status").write_text("Name:\tjob\nNSpid:\t12345\t3771\n")
    (other_process / "status").write_text("Name:\tother\n")
    monkeypatch.setenv("HOST_PROC", str(host_proc))

    mock_get_subprocess_output.side_effect = [
        (mock_output('scontrol.txt'), "", 0),
        ("c1", "", 0),
        (mock_output('scontrol_squeue.txt'), "", 0),
        (mock_output('scontrol_squeue2.txt'), "", 0),
    ]

    check.check(None)

    aggregator.assert_metric(
        name='slurm.scontrol.jobs.info',
        value=1,
        tags=[
            "nspid:3771",
            "pid:12345",
            "slurm_global_id:0",
            "slurm_job_id:14",
            "slurm_local_id:0",
            "slurm_node_name:c1",
            "slurm_step_id:batch",
            "slurm_job_name:my_job",
            "slurm_job_state:RUNNING",
            "slurm_job_user:root",
        ],
    )
    aggregator.assert_metric(
        name='slurm.scontrol.jobs.info',
        value=1,
        tags=[
            "pid:3772",
            "slurm_global_id:-",
            "slurm_job_id:14",
            "slurm_local_id:-",
            "slurm_node_name:c1",
            "slurm_step_id:batch",
            "slurm_job_name:my_job",
            "slurm_job_state:RUNNING",
            "slurm_job_user:root",
        ],
    )
    aggregator.assert_metric(
        name='slurm.scontrol.jobs.info',
        value=1,
        tags=[
            "pid:3773",
            "slurm_global_id:0",
            "slurm_job_id:15",
            "slurm_local_id:0",
            "slurm_node_name:c1",
            "slurm_step_id:batch",
            "slurm_job_name:my_job2",
            "slurm_job_state:RUNNING",
            "slurm_job_user:root",
        ],
    )
    aggregator.assert_all_metrics_covered()


@patch('datadog_checks.slurm.check.get_subprocess_output')
def test_scontrol_processing_does_not_resolve_host_pid_by_default(
    mock_get_subprocess_output, instance, aggregator, monkeypatch, tmp_path
):
    instance['collect_scontrol_stats'] = True
    check = SlurmCheck('slurm', {}, [instance])
    host_proc = tmp_path / "proc"
    host_process = host_proc / "12345"
    host_process.mkdir(parents=True)
    (host_process / "status").write_text("Name:\tjob\nNSpid:\t12345\t3771\n")
    monkeypatch.setenv("HOST_PROC", str(host_proc))

    mock_get_subprocess_output.side_effect = [
        (mock_output('scontrol.txt'), "", 0),
        ("c1", "", 0),
        (mock_output('scontrol_squeue.txt'), "", 0),
        (mock_output('scontrol_squeue2.txt'), "", 0),
    ]

    check.check(None)

    for metric in SCONTROL_MAP['metrics']:
        aggregator.assert_metric(name=metric['name'], value=metric['value'], tags=metric['tags'])
    aggregator.assert_all_metrics_covered()


def test_resolve_scontrol_host_pid_logs_multiple_matches(instance, caplog):
    check = SlurmCheck('slurm', {}, [instance])
    first_match = ProcessPidMatch(host_pid="1", namespace_pids=["1"])
    second_match = ProcessPidMatch(host_pid="12345", namespace_pids=["12345", "1"])

    assert check._resolve_scontrol_host_pid("1", {"1": [first_match, second_match]}) == second_match
    assert "Found multiple host PID matches for scontrol namespace PID 1" in caplog.text


def test_resolve_scontrol_host_pid_returns_match_without_nspids_when_missing(instance):
    check = SlurmCheck('slurm', {}, [instance])

    assert check._resolve_scontrol_host_pid("3771", {}) == ProcessPidMatch(host_pid="3771", namespace_pids=[])


@patch('datadog_checks.slurm.check.get_subprocess_output')
@patch('datadog_checks.slurm.check.SlurmCheck._get_process_tags')
def test_scontrol_processing_gets_process_tags_for_host_pid_only(
    mock_get_process_tags, mock_get_subprocess_output, instance, monkeypatch, tmp_path
):
    instance['collect_scontrol_stats'] = True
    instance['resolve_scontrol_host_pids'] = True
    check = SlurmCheck('slurm', {}, [instance])
    host_proc = tmp_path / "proc"
    host_process = host_proc / "12345"
    host_process.mkdir(parents=True)
    (host_process / "status").write_text("Name:\tjob\nNSpid:\t12345\t3771\n")
    monkeypatch.setenv("HOST_PROC", str(host_proc))
    mock_get_process_tags.return_value = []
    mock_get_subprocess_output.side_effect = [
        (mock_output('scontrol.txt'), "", 0),
        ("c1", "", 0),
        (mock_output('scontrol_squeue.txt'), "", 0),
        (mock_output('scontrol_squeue2.txt'), "", 0),
    ]

    check.check(None)

    mock_get_process_tags.assert_any_call("12345")
    mock_get_process_tags.assert_any_call("3772")
    mock_get_process_tags.assert_any_call("3773")
    assert mock_get_process_tags.call_count == 3


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


@patch('datadog_checks.slurm.check.get_subprocess_output')
def test_process_seff_metric_submission(mock_get_subprocess_output, instance, aggregator):
    # Load the seff fixture
    with open('tests/fixtures/seff.txt') as f:
        seff_output = f.read()

    mock_get_subprocess_output.return_value = (seff_output, '', 0)
    instance['collect_seff_stats'] = True
    check = SlurmCheck('slurm', {}, [instance])
    tags = ["slurm_job_id:101", "custom:tag"]
    check.process_seff("101", tags)

    aggregator.assert_metric('slurm.seff.cpu_utilized', value=1.0, tags=tags)
    aggregator.assert_metric('slurm.seff.cpu_efficiency', value=20.0, tags=tags)
    aggregator.assert_metric('slurm.seff.memory_utilized_mb', value=0.0, tags=tags)
    aggregator.assert_metric('slurm.seff.memory_efficiency', value=0.0, tags=tags)
    aggregator.assert_all_metrics_covered()


def test_sinfo_gpu_gres_slurm_2505(instance, aggregator):
    # Slurm 25.05 sinfo appends a socket-affinity suffix, e.g. 'gpu:<type>:8(S:0-1)', to GRES.
    # The count parser must ignore the suffix so gpu_total is still emitted (regression).
    check = SlurmCheck('slurm', {}, [instance])
    check.process_sinfo_node(mock_output('sinfo_gres_2505.txt'))

    gpu_type = 'slurm_node_gpu_type:nvidia_rtx_pro_6000_blackwell_server_edition'
    node1 = [
        'slurm_partition_name:rtx-pro',
        'slurm_node_name:slurm-rtx-pro-129-015',
        'slurm_cluster_name:N/A',
        gpu_type,
    ]
    node2 = [
        'slurm_partition_name:rtx-pro',
        'slurm_node_name:slurm-rtx-pro-134-237',
        'slurm_cluster_name:N/A',
        gpu_type,
    ]
    aggregator.assert_metric('slurm.node.gpu_total', value=8, tags=node1)
    aggregator.assert_metric('slurm.node.gpu_used', value=3, tags=node1)
    aggregator.assert_metric('slurm.node.gpu_total', value=8, tags=node2)
    aggregator.assert_metric('slurm.node.gpu_used', value=0, tags=node2)


def test_sinfo_gpu_gres_multi_type(instance, aggregator):
    # A node advertising multiple GPU models renders a comma-separated GRES list, e.g.
    # 'gpu:tesla:2,gpu:kepler:2'. Every type must be counted, not just the first entry.
    check = SlurmCheck('slurm', {}, [instance])
    check.process_sinfo_node(mock_output('sinfo_gres_multi_2505.txt'))

    base = [
        'slurm_partition_name:rtx-pro',
        'slurm_node_name:slurm-mixed-gpu-001',
        'slurm_cluster_name:N/A',
    ]
    tesla = base + ['slurm_node_gpu_type:tesla']
    kepler = base + ['slurm_node_gpu_type:kepler']
    aggregator.assert_metric('slurm.node.gpu_total', value=2, tags=tesla)
    aggregator.assert_metric('slurm.node.gpu_used', value=1, tags=tesla)
    aggregator.assert_metric('slurm.node.gpu_total', value=2, tags=kepler)
    aggregator.assert_metric('slurm.node.gpu_used', value=0, tags=kepler)


@patch('datadog_checks.slurm.check.get_subprocess_output')
def test_process_seff_normalizes_kilobytes(mock_get_subprocess_output, instance, aggregator):
    # Slurm 25.05 seff reports small jobs in KB (and large ones in GB); memory must still
    # normalize to MB rather than being dropped (regression for the hardcoded 'MB').
    mock_get_subprocess_output.return_value = (mock_output('seff_2505.txt'), '', 0)
    instance['collect_seff_stats'] = True
    check = SlurmCheck('slurm', {}, [instance])
    tags = ["slurm_job_id:317"]
    check.process_seff("317", tags)

    aggregator.assert_metric('slurm.seff.memory_utilized_mb', value=0.7578125, tags=tags)
    aggregator.assert_metric('slurm.seff.cpu_utilized', value=0.0, tags=tags)


def test_sacct_running_job_skips_none_avgcpu(instance, aggregator):
    # RUNNING jobs report an empty AveCPU; avgcpu must be skipped rather than submitted as
    # None (regression: previously only duration had a None guard).
    check = SlurmCheck('slurm', {}, [instance])
    running_job = (
        "315|dd-fix-run|rtx-pro|cw-sup|12|billing=12,cpu=12,gres/gpu=1,mem=93585408K,node=1|"
        "00:00:12|144|||||RUNNING|0:0|2026-07-10T18:45:32|Unknown|slurm-rtx-pro-129-015|||"
    )
    check.process_sacct(running_job)

    aggregator.assert_metric('slurm.sacct.slurm_job_avgcpu', count=0)
    aggregator.assert_metric('slurm.sacct.job.duration', value=12, count=1)
    aggregator.assert_metric('slurm.sacct.job.info', value=1, count=1)
