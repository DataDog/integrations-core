# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.ibm_spectrum_lsf import IbmSpectrumLsfCheck

from .common import ALL_METRICS, BJOBS_METRICS, CLUSTER_METRICS
from .conftest import get_mock_output


def test_lsid_err(mock_client, dd_run_check, aggregator, instance, caplog):
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    mock_client.lsid.return_value = (None, "Can't connect to LIM", 1)
    dd_run_check(check)

    aggregator.assert_metric("ibm_spectrum_lsf.can_connect", 0)
    assert "Failed to get lsid output: Can't connect to LIM. Skipping check" in caplog.text
    aggregator.assert_all_metrics_covered()


def test_check(mock_client, dd_run_check, aggregator, instance):
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client

    dd_run_check(check)

    for metric in ALL_METRICS:
        aggregator.assert_metric(metric["name"], metric["val"], tags=metric["tags"])

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_symmetric_inclusion=True)


def test_check_tags(mock_client, dd_run_check, aggregator, instance):
    tag_instance = instance
    tag_instance['tags'] = ["test_check"]
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client

    dd_run_check(check)

    for metric in ALL_METRICS:
        aggregator.assert_metric(metric["name"], metric["val"], tags=metric["tags"] + ["test_check"])

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_lscluster_error(mock_client, dd_run_check, aggregator, instance):
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    mock_client.lsclusters.return_value = (None, "Can't connect", 1)
    dd_run_check(check)

    for metric in ALL_METRICS:
        if metric not in CLUSTER_METRICS:
            aggregator.assert_metric(metric["name"], metric["val"], tags=metric["tags"])

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_lscluster_wrong_column_num(mock_client, dd_run_check, aggregator, instance):
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    mock_client.lsclusters.return_value = get_mock_output('lsclusters_err')
    dd_run_check(check)

    for metric in ALL_METRICS:
        if metric not in CLUSTER_METRICS:
            aggregator.assert_metric(metric["name"], metric["val"], tags=metric["tags"])

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_lsload_extra_output(mock_client, dd_run_check, aggregator, instance, caplog):
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    mock_client.lsload.return_value = get_mock_output('lsload_extra_text')
    caplog.set_level(logging.DEBUG)
    dd_run_check(check)

    for metric in ALL_METRICS:
        aggregator.assert_metric(metric["name"], metric["val"], tags=metric["tags"])

    assert "Unexpected row length from lsload: 1, expected 13" in caplog.text

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_bjobs_no_output(mock_client, dd_run_check, aggregator, instance, caplog):
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    mock_client.bjobs.return_value = get_mock_output('bjobs_no_jobs')
    caplog.set_level(logging.DEBUG)
    dd_run_check(check)

    for metric in ALL_METRICS:
        if metric not in BJOBS_METRICS:
            aggregator.assert_metric(metric["name"], metric["val"], tags=metric["tags"])

    assert "Skipping bjobs metrics; unexpected cli command output. Number of columns: 1, expected: 12" in caplog.text

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
