# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.ibm_spectrum_lsf import IbmSpectrumLsfCheck

from .common import ALL_METRICS, BHOST_METRICS, LSID_METRICS
from .conftest import get_mock_output


def test_lsid_err(mock_client, dd_run_check, aggregator, instance, caplog):
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    mock_client.lsid.side_effect = lambda: (None, "Can't connect to LIM", 1)
    dd_run_check(check)

    aggregator.assert_metric("ibm_spectrum_lsf.can_connect", 0)
    assert "Failed to get lsid output: Can't connect to LIM. Skipping check" in caplog.text
    aggregator.assert_all_metrics_covered()


def test_check(mock_client, dd_run_check, aggregator, instance):
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    dd_run_check(check)

    for metric in ALL_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_lscluster_error(mock_client, dd_run_check, aggregator, instance):
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    mock_client.lsclusters.side_effect = lambda *args, **kwargs: (None, "Can't connect", 1)
    dd_run_check(check)

    for metric in LSID_METRICS + BHOST_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_lscluster_wrong_column_num(mock_client, dd_run_check, aggregator, instance):
    check = IbmSpectrumLsfCheck('ibm_spectrum_lsf', {}, [instance])
    check.client = mock_client
    mock_client.lsclusters.side_effect = lambda *args, **kwargs: get_mock_output('lsclusters_err')
    dd_run_check(check)

    for metric in LSID_METRICS + BHOST_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
