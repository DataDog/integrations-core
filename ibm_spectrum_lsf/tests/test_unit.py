# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
from typing import Any

import pytest
from mock import call, patch

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.ibm_spectrum_lsf import IbmSpectrumLsfCheck

from .common import (
    ALL_DEFAULT_METRICS,
    ALL_METRICS,
    BADMIN_PERFMON_METRICS,
    BJOBS_METRICS,
    CLUSTER_METRICS,
    LHOST_METRICS,
    LSID_METRICS,
    LSLOAD_METRICS,
)
from .conftest import get_mock_output


def assert_metrics(
    metrics_to_assert: list[dict[str, Any]], metrics_to_exclude: list[dict[str, Any]], aggregator: AggregatorStub
):
    for metric in metrics_to_assert:
        if metric not in metrics_to_exclude:
            aggregator.assert_metric(metric["name"], metric["val"], tags=metric["tags"])


def test_lsid_err(mock_client, dd_run_check, aggregator, instance, caplog):
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    mock_client.lsid.return_value = ("", "Can't connect to LIM", 1)
    dd_run_check(check)

    aggregator.assert_metric("ibm_spectrum_lsf.can_connect", 0)
    assert "Failed to get lsid output: Can't connect to LIM. Skipping check" in caplog.text
    aggregator.assert_all_metrics_covered()


def test_check(mock_client, dd_run_check, aggregator, instance):
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client

    dd_run_check(check)

    assert_metrics(ALL_DEFAULT_METRICS, [], aggregator)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_check_gpu_enabled(mock_client, dd_run_check, aggregator, instance):
    instance["metric_sources"] = [
        'lsclusters',
        'lshosts',
        'bhosts',
        'lsload',
        'bqueues',
        'bslots',
        'bjobs',
        'lsload_gpu',
        'bhosts_gpu',
    ]
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client

    dd_run_check(check)

    assert_metrics(ALL_METRICS, BADMIN_PERFMON_METRICS, aggregator)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_check_all_metric_sources(mock_client, dd_run_check, aggregator, instance):
    instance["metric_sources"] = [
        'lsclusters',
        'lshosts',
        'bhosts',
        'lsload',
        'bqueues',
        'bslots',
        'bjobs',
        'lsload_gpu',
        'bhosts_gpu',
        'badmin_perfmon',
    ]
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client

    dd_run_check(check)

    assert_metrics(ALL_METRICS, [], aggregator)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_symmetric_inclusion=True)


def test_check_tags(mock_client, dd_run_check, aggregator, instance):
    tag_instance = instance
    tag_instance['tags'] = ["test_check"]
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client

    dd_run_check(check)

    for metric in ALL_DEFAULT_METRICS:
        aggregator.assert_metric(metric["name"], metric["val"], tags=metric["tags"] + ["test_check"])

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_lscluster_error(mock_client, dd_run_check, aggregator, instance):
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    mock_client.lsclusters.return_value = ("", "Can't connect", 1)
    dd_run_check(check)

    assert_metrics(ALL_DEFAULT_METRICS, CLUSTER_METRICS, aggregator)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_lscluster_wrong_column_num(mock_client, dd_run_check, aggregator, instance):
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    mock_client.lsclusters.return_value = get_mock_output('lsclusters_err')
    dd_run_check(check)

    assert_metrics(ALL_DEFAULT_METRICS, CLUSTER_METRICS, aggregator)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_lsload_extra_output(mock_client, dd_run_check, aggregator, instance, caplog):
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    mock_client.lsload.return_value = get_mock_output('lsload_extra_text')
    caplog.set_level(logging.DEBUG)
    dd_run_check(check)

    assert_metrics(ALL_DEFAULT_METRICS, [], aggregator)

    assert "Unexpected row length from lsload: 1, expected 13" in caplog.text

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_bjobs_no_output(mock_client, dd_run_check, aggregator, instance, caplog):
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    mock_client.bjobs.return_value = get_mock_output('bjobs_no_jobs')
    caplog.set_level(logging.DEBUG)
    dd_run_check(check)

    assert_metrics(ALL_DEFAULT_METRICS, BJOBS_METRICS, aggregator)

    assert "Skipping bjobs metrics; unexpected cli command output. Number of columns: 1, expected: 12" in caplog.text

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_client_calls(dd_run_check, aggregator, instance):
    # assert that subprocess.run is called with the correct arguments
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.stdout = get_mock_output('lsid')[0]
        mock_run.return_value.stderr = ""
        mock_run.return_value.returncode = 0
        dd_run_check(check)
        # assert some expected calls are happening when not mocking the client
        assert call(('lsid',), timeout=5, capture_output=True, text=True) in mock_run.call_args_list
        assert (
            call(
                ('lsload', '-o', "HOST_NAME status r15s r1m r15m ut pg io ls it tmp swp mem delimiter='|'"),
                timeout=5,
                capture_output=True,
                text=True,
            )
            in mock_run.call_args_list
        )


def test_client_error(dd_run_check, aggregator, instance, caplog):
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = FileNotFoundError("LSID command not found")
        dd_run_check(check)
        assert "Failed to get lsid output: LSID command not found. Skipping check" in caplog.text
        aggregator.assert_metric("ibm_spectrum_lsf.can_connect", 0)
        aggregator.assert_all_metrics_covered()
        aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_check_metric_sources_all(mock_client, dd_run_check, aggregator, instance):
    instance["metric_sources"] = [
        'lsclusters',
        'lshosts',
        'bhosts',
        'lsload',
        'bqueues',
        'bslots',
        'bjobs',
        'lsload_gpu',
        'bhosts_gpu',
        'badmin_perfmon',
    ]
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    dd_run_check(check)
    assert_metrics(ALL_METRICS, [], aggregator)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_check_metric_sources_invalid(mock_client, dd_run_check, instance):
    instance["metric_sources"] = ['test']
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    with pytest.raises(Exception, match="Invalid metric source: test"):
        dd_run_check(check)


def test_check_metric_sources_subset(mock_client, dd_run_check, aggregator, instance):
    instance["metric_sources"] = ['lsclusters', 'lshosts']
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    dd_run_check(check)

    assert_metrics(CLUSTER_METRICS + LHOST_METRICS + LSID_METRICS, [], aggregator)


def test_no_output_from_command(mock_client, dd_run_check, aggregator, instance, caplog):
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    mock_client.lsload.return_value = ("", "", 0)
    caplog.set_level(logging.WARNING)
    dd_run_check(check)

    assert_metrics(ALL_DEFAULT_METRICS, LSLOAD_METRICS, aggregator)

    assert "No output from command lsload" in caplog.text

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_badmin_perfmon(mock_client, dd_run_check, aggregator, instance):
    instance['metric_sources'] = ['badmin_perfmon']
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    dd_run_check(check)

    assert_metrics(BADMIN_PERFMON_METRICS + LSID_METRICS, [], aggregator)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_badmin_perfmon_start_only_called_once(mock_client, dd_run_check, aggregator, instance):
    instance['metric_sources'] = ['badmin_perfmon']
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    dd_run_check(check)
    dd_run_check(check)
    dd_run_check(check)
    dd_run_check(check)
    dd_run_check(check)

    assert mock_client.badmin_perfmon_start.call_count == 1
    assert mock_client.badmin_perfmon_start.call_args_list == [call(15)]

    assert_metrics(BADMIN_PERFMON_METRICS + LSID_METRICS, [], aggregator)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.parametrize(
    'min_collection_interval, metric_sources, expected_call_count, expected_call_args, expected_metrics',
    [
        pytest.param(
            15,
            [
                'badmin_perfmon',
            ],
            1,
            [call(15)],
            BADMIN_PERFMON_METRICS + LSID_METRICS,
            id='no change',
        ),
        pytest.param(
            60,
            ['badmin_perfmon'],
            1,
            [call(60)],
            BADMIN_PERFMON_METRICS + LSID_METRICS,
            id='default collection interval',
        ),
        pytest.param(
            300,
            ['badmin_perfmon', 'lsclusters'],
            1,
            [call(300)],
            BADMIN_PERFMON_METRICS + LSID_METRICS + CLUSTER_METRICS,
            id='high collection interval',
        ),
        pytest.param(
            60,
            ['lsclusters', 'lshosts', 'bhosts', 'lsload', 'bqueues', 'bslots', 'bjobs', 'lsload_gpu', 'bhosts_gpu'],
            0,
            [],
            ALL_DEFAULT_METRICS,
            id='no badmin_perfmon',
        ),
        pytest.param(
            60,
            [
                'badmin_perfmon',
                'lsclusters',
                'lshosts',
                'bhosts',
                'lsload',
                'bqueues',
                'bslots',
                'bjobs',
                'lsload_gpu',
                'bhosts_gpu',
            ],
            1,
            [call(60)],
            ALL_METRICS,
            id='all metrics',
        ),
    ],
)
def test_badmin_perfmon_start_diff_configs(
    mock_client,
    dd_run_check,
    aggregator,
    instance,
    min_collection_interval,
    metric_sources,
    expected_call_count,
    expected_call_args,
    expected_metrics,
):
    instance['metric_sources'] = metric_sources
    instance['min_collection_interval'] = min_collection_interval
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    dd_run_check(check)

    assert mock_client.badmin_perfmon_start.call_count == expected_call_count
    assert mock_client.badmin_perfmon_start.call_args_list == expected_call_args

    assert_metrics(expected_metrics, [], aggregator)


def test_badmin_perfmon_start_unknown_metric(mock_client, dd_run_check, aggregator, instance, caplog):
    instance['metric_sources'] = ['badmin_perfmon']
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    caplog.set_level(logging.DEBUG)
    mock_client.badmin_perfmon.return_value = get_mock_output('badmin_perfmon_view_invalid_metrics')
    dd_run_check(check)

    assert (
        "Skipping metric record with missing name Job information: {'name': 'Job information',"
        " 'current': 11, 'max': 13, 'min': 11, 'avg': 12, 'total': 24}" in caplog.text
    )

    assert_metrics(BADMIN_PERFMON_METRICS + LSID_METRICS, [], aggregator)

    aggregator.assert_all_metrics_covered()


def test_badmin_perfmon_start_unknown_aggregation(mock_client, dd_run_check, aggregator, instance, caplog):
    instance['metric_sources'] = ['badmin_perfmon']
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    caplog.set_level(logging.DEBUG)
    mock_client.badmin_perfmon.return_value = get_mock_output('badmin_perfmon_view_invalid_aggregation')
    dd_run_check(check)

    assert (
        "Skipping metric aggregation with missing value current: {'name': 'Job submission requests',"
        " 'last': 0, 'max': 3, 'min': 0, 'avg': 1, 'total': 3}" in caplog.text
    )

    assert_metrics(
        BADMIN_PERFMON_METRICS + LSID_METRICS,
        [
            {
                'name': 'ibm_spectrum_lsf.perfmon.jobs.submission_requests.current',
                'tags': ['lsf_cluster_name:test-cluster'],
                'val': 0,
            }
        ],
        aggregator,
    )

    aggregator.assert_all_metrics_covered()


def test_badmin_perfmon_no_output(mock_client, dd_run_check, aggregator, instance, caplog):
    instance['metric_sources'] = ['badmin_perfmon']
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    caplog.set_level(logging.WARNING)
    mock_client.badmin_perfmon.return_value = ("", "Invalid Command", 1)
    dd_run_check(check)

    assert "Failed to get badmin_perfmon output: Invalid Command" in caplog.text

    assert_metrics(LSID_METRICS, [], aggregator)
    aggregator.assert_all_metrics_covered()


def test_badmin_perfmon_invalid_json(mock_client, dd_run_check, aggregator, instance, caplog):
    instance['metric_sources'] = ['badmin_perfmon']
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    caplog.set_level(logging.WARNING)
    mock_client.badmin_perfmon.return_value = ("Invalid JSON", "", 0)
    dd_run_check(check)

    assert "Invalid JSON output from badmin_perfmon: Invalid JSON" in caplog.text

    assert_metrics(LSID_METRICS, [], aggregator)
    aggregator.assert_all_metrics_covered()


def test_badmin_perfmon_stop(mock_client, dd_run_check, aggregator, instance):
    instance['metric_sources'] = ['badmin_perfmon']
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    dd_run_check(check)
    dd_run_check(check)
    assert mock_client.badmin_perfmon_stop.call_count == 0
    check.cancel()
    assert mock_client.badmin_perfmon_stop.call_count == 1


def test_cancel_no_badmin_perfmon(mock_client, dd_run_check, aggregator, instance):
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    dd_run_check(check)
    check.cancel()
    assert mock_client.badmin_perfmon_stop.call_count == 0


def test_badmin_perfmon_collection_not_started_auto(mock_client, dd_run_check, aggregator, instance, caplog):
    instance['metric_sources'] = ['badmin_perfmon']
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    mock_client.badmin_perfmon.return_value = get_mock_output('badmin_perfmon_view_collection_not_started')
    dd_run_check(check)
    assert_metrics(LSID_METRICS, [], aggregator)

    # no metrics collected, start collection
    assert mock_client.badmin_perfmon_start.call_count == 2
    mock_client.badmin_perfmon.return_value = get_mock_output('badmin_perfmon_view')

    dd_run_check(check)
    # collection started, no need to start again
    assert mock_client.badmin_perfmon_start.call_count == 2
    assert_metrics(BADMIN_PERFMON_METRICS + LSID_METRICS, [], aggregator)

    aggregator.assert_all_metrics_covered()


def test_badmin_perfmon_collection_not_started_manual(mock_client, dd_run_check, aggregator, instance, caplog):
    instance['metric_sources'] = ['badmin_perfmon']
    instance['badmin_perfmon_auto'] = False
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    mock_client.badmin_perfmon.return_value = get_mock_output('badmin_perfmon_view_collection_not_started')

    dd_run_check(check)
    dd_run_check(check)
    dd_run_check(check)
    check.cancel()

    assert_metrics(LSID_METRICS, [], aggregator)
    assert mock_client.badmin_perfmon_start.call_count == 0
    assert mock_client.badmin_perfmon_stop.call_count == 0
