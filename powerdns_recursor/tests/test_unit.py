# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from copy import deepcopy

import mock
import pytest
import requests

from datadog_checks.dev.http import MockResponse
from datadog_checks.powerdns_recursor import PowerDNSRecursorCheck

from . import common, metrics

pytestmark = pytest.mark.unit

STATS_URL = "http://{}:{}/servers/localhost/statistics".format(common.HOST, common.PORT)
STATS_URL_V4 = "http://{}:{}/api/v1/servers/localhost/statistics".format(common.HOST, common.PORT)


def test_bad_config(aggregator):
    check = PowerDNSRecursorCheck("powerdns_recursor", {}, [common.BAD_CONFIG])
    with pytest.raises(Exception):
        check.check(common.BAD_CONFIG)

    service_check_tags = common._config_sc_tags(common.BAD_CONFIG)
    aggregator.assert_service_check('powerdns.recursor.can_connect', status=check.CRITICAL, tags=service_check_tags)
    assert len(aggregator._metrics) == 0


def test_very_bad_config(aggregator):
    for config in [{}, {"host": "localhost"}, {"port": 1000}, {"host": "localhost", "port": 1000}]:
        check = PowerDNSRecursorCheck("powerdns_recursor", {}, [config])
        with pytest.raises(Exception):
            check.check(config)

    assert len(aggregator._metrics) == 0


def test_api_key_headers():
    instance = deepcopy(common.CONFIG)
    instance.update({'api_key': 'API_KEY', 'headers': {'foo': 'bar'}})
    expected_headers = {'X-API-Key': 'API_KEY', 'foo': 'bar'}

    check = PowerDNSRecursorCheck('powerdns_recursor', {}, instances=[instance])
    assert expected_headers == check.http.options['headers']


def test_check_missing_param_raises_formatted_exception():
    # Kills the core/ZeroIterationForLoop mutant at powerdns_recursor.py:134 (required -> [])
    # and the core/ReplaceBinaryOperator_Mod_* mutants at powerdns_recursor.py:136 ('%s' % vs +/-/*/... (param)).
    instance = {'port': common.PORT}
    check = PowerDNSRecursorCheck("powerdns_recursor", {}, [instance])

    # Mocked so that, if the missing-param check were skipped, check() would run to completion
    # against a fake response instead of attempting a real network call.
    with mock.patch('requests.Session.get', return_value=MockResponse(json_data=[])):
        with pytest.raises(Exception) as exc_info:
            check.check(instance)

    assert type(exc_info.value) is Exception
    assert str(exc_info.value) == "powerdns_recursor instance missing host. Skipping."


def test_check_defaults_none_tags_to_empty_list(aggregator):
    # Kills the core/ReplaceComparisonOperator_Is_IsNot and core/AddNot mutants at powerdns_recursor.py:142
    # (tags is None -> tags is not None / not tags is None).
    instance = deepcopy(common.CONFIG)
    instance['tags'] = None
    stats = [{'name': metrics.GAUGE_METRICS[0], 'value': '1'}]
    check = PowerDNSRecursorCheck("powerdns_recursor", {}, [instance])

    with mock.patch('requests.Session.get', return_value=MockResponse(json_data=stats)):
        check.check(instance)

    aggregator.assert_metric(metrics.METRIC_FORMAT.format(metrics.GAUGE_METRICS[0]), count=1, tags=[])


def test_check_preserves_provided_tags(aggregator):
    # Companion to test_check_defaults_none_tags_to_empty_list: confirms line 142 doesn't
    # clobber tags that were already provided (would also catch the mutants above).
    instance = deepcopy(common.CONFIG)
    instance['tags'] = ['foo:bar']
    stats = [{'name': metrics.GAUGE_METRICS[0], 'value': '1'}]
    check = PowerDNSRecursorCheck("powerdns_recursor", {}, [instance])

    with mock.patch('requests.Session.get', return_value=MockResponse(json_data=stats)):
        check.check(instance)

    aggregator.assert_metric(metrics.METRIC_FORMAT.format(metrics.GAUGE_METRICS[0]), count=1, tags=['foo:bar'])


def test_check_v3_only_collects_base_metrics(aggregator):
    # Kills the core/ZeroIterationForLoop mutant at powerdns_recursor.py:117 (stats -> []) and the
    # core/AddNot mutant at powerdns_recursor.py:118 (gauge/rate metric routing), and the
    # core/ReplaceComparisonOperator_Eq_* / AddNot / NumberReplacer mutants at powerdns_recursor.py:124
    # (config.version == 4) for a non-4 version.
    instance = deepcopy(common.CONFIG)
    stats = [
        {'name': metrics.GAUGE_METRICS[0], 'value': '1'},
        {'name': metrics.RATE_METRICS[0], 'value': '2'},
        {'name': metrics.GAUGE_METRICS_V4[0], 'value': '3'},
        {'name': metrics.RATE_METRICS_V4[0], 'value': '4'},
    ]
    check = PowerDNSRecursorCheck("powerdns_recursor", {}, [instance])

    with mock.patch('requests.Session.get', return_value=MockResponse(json_data=stats)):
        check.check(instance)

    aggregator.assert_metric(
        metrics.METRIC_FORMAT.format(metrics.GAUGE_METRICS[0]), count=1, metric_type=aggregator.GAUGE
    )
    aggregator.assert_metric(
        metrics.METRIC_FORMAT.format(metrics.RATE_METRICS[0]), count=1, metric_type=aggregator.RATE
    )
    aggregator.assert_metric(metrics.METRIC_FORMAT.format(metrics.GAUGE_METRICS_V4[0]), count=0)
    aggregator.assert_metric(metrics.METRIC_FORMAT.format(metrics.RATE_METRICS_V4[0]), count=0)


def test_check_v4_also_collects_v4_metrics(aggregator):
    # Kills the remaining core/ReplaceComparisonOperator_Eq_* / AddNot / NumberReplacer mutants at
    # powerdns_recursor.py:124 and the core/AddNot mutant at powerdns_recursor.py:125 (v4 metric
    # routing) that test_check_v3_only_collects_base_metrics can't distinguish for version == 4.
    instance = deepcopy(common.CONFIG_V4)
    stats = [
        {'name': metrics.GAUGE_METRICS[0], 'value': '1'},
        {'name': metrics.RATE_METRICS[0], 'value': '2'},
        {'name': metrics.GAUGE_METRICS_V4[0], 'value': '3'},
        {'name': metrics.RATE_METRICS_V4[0], 'value': '4'},
    ]
    check = PowerDNSRecursorCheck("powerdns_recursor", {}, [instance])

    with mock.patch('requests.Session.get', return_value=MockResponse(json_data=stats)):
        check.check(instance)

    aggregator.assert_metric(
        metrics.METRIC_FORMAT.format(metrics.GAUGE_METRICS[0]), count=1, metric_type=aggregator.GAUGE
    )
    aggregator.assert_metric(
        metrics.METRIC_FORMAT.format(metrics.RATE_METRICS[0]), count=1, metric_type=aggregator.RATE
    )
    aggregator.assert_metric(
        metrics.METRIC_FORMAT.format(metrics.GAUGE_METRICS_V4[0]), count=1, metric_type=aggregator.GAUGE
    )
    aggregator.assert_metric(
        metrics.METRIC_FORMAT.format(metrics.RATE_METRICS_V4[0]), count=1, metric_type=aggregator.RATE
    )


def test_check_selects_v4_url_based_on_version(aggregator, datadog_agent):
    # Kills the core/ReplaceComparisonOperator_Eq_* / AddNot / NumberReplacer mutants at
    # powerdns_recursor.py:164 (config.version == 4 url selection).
    # Metadata collection is disabled so the mocked GET call captured below is unambiguously
    # the one made for statistics collection.
    datadog_agent._config['enable_metadata_collection'] = False

    for version, expected_url in [(4, STATS_URL_V4), (3, STATS_URL), (5, STATS_URL)]:
        instance = deepcopy(common.CONFIG)
        instance['version'] = version
        check = PowerDNSRecursorCheck("powerdns_recursor", {}, [instance])
        with mock.patch('requests.Session.get', return_value=MockResponse(json_data=[])) as mock_get:
            check.check(instance)
        assert mock_get.call_args[0][0] == expected_url


def test_check_falls_back_to_v4_url_after_failure(aggregator, datadog_agent):
    # Kills the core/ExceptionReplacer mutant at powerdns_recursor.py:170 (except Exception) and the
    # core/ReplaceComparisonOperator_Is_* / AddNot mutants at powerdns_recursor.py:171 (url_v4 is url)
    # for the non-v4 case, where a failed request should retry against the v4 URL.
    datadog_agent._config['enable_metadata_collection'] = False
    instance = deepcopy(common.CONFIG)
    instance['version'] = 3
    stats = [{'name': metrics.GAUGE_METRICS[0], 'value': '1'}]
    check = PowerDNSRecursorCheck("powerdns_recursor", {}, [instance])

    with mock.patch(
        'requests.Session.get', side_effect=[requests.exceptions.ConnectionError('boom'), MockResponse(json_data=stats)]
    ) as mock_get:
        check.check(instance)

    assert mock_get.call_count == 2
    aggregator.assert_metric(metrics.METRIC_FORMAT.format(metrics.GAUGE_METRICS[0]), count=1)
    aggregator.assert_service_check(
        'powerdns.recursor.can_connect', status=check.OK, tags=common._config_sc_tags(instance)
    )


def test_check_reraises_without_retry_when_already_v4(aggregator, datadog_agent):
    # Kills the core/ReplaceComparisonOperator_Is_* / AddNot mutants at powerdns_recursor.py:171
    # (url_v4 is url) for the v4 case, where a failed request must not be retried a second time.
    datadog_agent._config['enable_metadata_collection'] = False
    instance = deepcopy(common.CONFIG_V4)
    check = PowerDNSRecursorCheck("powerdns_recursor", {}, [instance])

    with mock.patch('requests.Session.get', side_effect=[requests.exceptions.ConnectionError('boom')]) as mock_get:
        with pytest.raises(requests.exceptions.ConnectionError):
            check.check(instance)

    assert mock_get.call_count == 1
    aggregator.assert_service_check(
        'powerdns.recursor.can_connect', status=check.CRITICAL, tags=common._config_sc_tags(instance)
    )


def test_check_skips_metadata_collection_when_disabled(aggregator, datadog_agent):
    # Kills the core/RemoveDecorator mutant at powerdns_recursor.py:178
    # (@AgentCheck.metadata_entrypoint removed from _collect_metadata).
    datadog_agent._config['enable_metadata_collection'] = False
    instance = deepcopy(common.CONFIG)
    check = PowerDNSRecursorCheck("powerdns_recursor", {}, [instance])
    check.check_id = 'test:123'

    with mock.patch('requests.Session.get', return_value=MockResponse(json_data=[])) as mock_get:
        check.check(instance)

    # Only the statistics GET happens; a second GET would mean metadata collection ran anyway.
    assert mock_get.call_count == 1
    datadog_agent.assert_metadata_count(0)


def test_check_logs_on_metadata_request_failure(aggregator, datadog_agent):
    # Kills the core/ExceptionReplacer mutant at powerdns_recursor.py:185 (except Exception as e).
    instance = deepcopy(common.CONFIG)
    stats = [{'name': metrics.GAUGE_METRICS[0], 'value': '1'}]
    check = PowerDNSRecursorCheck("powerdns_recursor", {}, [instance])
    check.check_id = 'test:123'
    check.log = mock.MagicMock()

    with mock.patch(
        'requests.Session.get',
        side_effect=[MockResponse(json_data=stats), requests.exceptions.Timeout(), requests.exceptions.Timeout()],
    ):
        check.check(instance)

    check.log.debug.assert_called_with('Error collecting PowerDNS Recursor version: %s', '')


def test_check_without_server_header_logs_and_skips_metadata(aggregator, datadog_agent):
    # Kills the core/AddNot mutant at powerdns_recursor.py:189 (response.headers.get('Server')).
    instance = deepcopy(common.CONFIG)
    stats = [{'name': metrics.GAUGE_METRICS[0], 'value': '1'}]
    check = PowerDNSRecursorCheck("powerdns_recursor", {}, [instance])
    check.check_id = 'test:123'
    check.log = mock.MagicMock()

    with mock.patch('requests.Session.get', side_effect=[MockResponse(json_data=stats), MockResponse()]):
        check.check(instance)

    check.log.debug.assert_called_with("Couldn't find the PowerDNS Recursor Server version header")


def test_check_sets_version_from_server_header(aggregator, datadog_agent):
    # Kills the core/NumberReplacer mutants at powerdns_recursor.py:192
    # (Server header split('/')[1] -> [0] / [2]).
    instance = deepcopy(common.CONFIG)
    stats = [{'name': metrics.GAUGE_METRICS[0], 'value': '1'}]
    check = PowerDNSRecursorCheck("powerdns_recursor", {}, [instance])
    check.check_id = 'test:123'

    with mock.patch(
        'requests.Session.get',
        side_effect=[MockResponse(json_data=stats), MockResponse(headers={'Server': 'PowerDNS/4.0.9'})],
    ):
        check.check(instance)

    datadog_agent.assert_metadata(
        'test:123',
        {
            'version.scheme': 'semver',
            'version.major': '4',
            'version.minor': '0',
            'version.patch': '9',
            'version.raw': '4.0.9',
        },
    )
    datadog_agent.assert_metadata_count(5)


def test_check_logs_on_metadata_decode_failure(aggregator, datadog_agent):
    # Kills the core/ExceptionReplacer mutant at powerdns_recursor.py:194 (except Exception as e).
    instance = deepcopy(common.CONFIG)
    stats = [{'name': metrics.GAUGE_METRICS[0], 'value': '1'}]
    check = PowerDNSRecursorCheck("powerdns_recursor", {}, [instance])
    check.check_id = 'test:123'
    check.log = mock.MagicMock()

    with mock.patch(
        'requests.Session.get',
        side_effect=[MockResponse(json_data=stats), MockResponse(headers={'Server': 'wrong_stuff'})],
    ):
        check.check(instance)

    check.log.debug.assert_called_with('Error while decoding PowerDNS Recursor version: %s', 'list index out of range')
