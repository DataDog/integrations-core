# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import re

import mock
import pytest

from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import (
    HTTPClientConnectionError,
    HTTPClientReadTimeoutError,
    HTTPClientStatusError,
)
from datadog_checks.vault import Vault
from datadog_checks.vault.errors import ApiUnreachable
from datadog_checks.vault.vault import Leader

from .common import INSTANCES
from .metrics import MERKLE_WAL_METRICS, MERKLE_WAL_QUANTILES
from .utils import assert_all_metrics, get_fixture_path

pytestmark = pytest.mark.unit

API_URL = INSTANCES['main']['api_url']
LEADER_URL = f'{API_URL}/sys/leader'
HEALTH_URL = f'{API_URL}/sys/health'
METRICS_URL = f'{API_URL}/sys/metrics?format=prometheus'

LEADER_DATA = {'ha_enabled': False, 'is_self': True, 'leader_address': '', 'leader_cluster_address': ''}
HEALTH_DATA = {
    'cluster_id': '9e25ccdb-09ea-8bd8-0521-34cf3ef7a4cc',
    'cluster_name': 'vault-cluster-f5f44063',
    'initialized': True,
    'replication_dr_mode': 'disabled',
    'replication_performance_mode': 'disabled',
    'sealed': False,
    'server_time_utc': 1529357080,
    'standby': False,
    'version': '0.10.2',
}


def read_fixture(name):
    with open(get_fixture_path(name), 'rb') as f:
        return f.read()


@pytest.fixture
def vault_api(fake_http_response):
    """Serve healthy leader and health endpoints; tests override one by registering it again."""
    fake_http_response(LEADER_URL, json_data=LEADER_DATA)
    fake_http_response(HEALTH_URL, json_data=HEALTH_DATA)
    return fake_http_response


@pytest.fixture
def token_instance(tmp_path):
    token_file = tmp_path / 'token'
    token_file.write_text('the-token')
    inst = INSTANCES['main'].copy()
    inst['client_token_path'] = str(token_file)
    return inst


@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
def test_service_check_connect_ok_all_tags(aggregator, dd_run_check, global_tags, use_openmetrics, vault_api):
    instance = {'use_openmetrics': use_openmetrics}
    instance.update(INSTANCES['main'])
    c = Vault(Vault.CHECK_NAME, {}, [instance])

    dd_run_check(c)

    aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, tags=global_tags, count=1)


def test_service_check_500_fail(aggregator, dd_run_check, global_tags, fake_http_response):
    instance = {'use_openmetrics': False}
    instance.update(INSTANCES['main'])
    c = Vault(Vault.CHECK_NAME, {}, [instance])

    fake_http_response(LEADER_URL, status_code=500)
    fake_http_response(HEALTH_URL, status_code=500)
    with pytest.raises(
        Exception, match=r'^The Vault endpoint `{}.+?` returned 500$'.format(re.escape(instance['api_url']))
    ):
        dd_run_check(c, extract_message=True)

    aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, tags=global_tags, count=1)


@pytest.mark.parametrize(
    'outcome, expected_message',
    [
        pytest.param(
            HTTPClientConnectionError('Name or service not known'),
            r'^Error accessing Vault endpoint `http://foo.bar`: Name or service not known$',
            id='connection error',
        ),
        pytest.param(
            HTTPClientReadTimeoutError('read timed out'),
            r'^Vault endpoint `http://foo.bar` timed out after 10.0 seconds$',
            id='timeout',
        ),
        pytest.param(
            FakeHTTPResponse(content=b'not json', json_error=json.JSONDecodeError('Expecting value', 'not json', 0)),
            r'^The Vault endpoint `http://foo.bar` returned invalid json data: Expecting value',
            id='invalid json',
        ),
    ],
)
def test_api_unreachable(aggregator, fake_http, outcome, expected_message):
    instance = {'use_openmetrics': False}
    instance.update(INSTANCES['main'])
    c = Vault(Vault.CHECK_NAME, {}, [instance])

    fake_http.register_response('GET', 'http://foo.bar', outcome)
    with pytest.raises(ApiUnreachable, match=expected_message):
        c.access_api("http://foo.bar", ignore_status_codes=None)

    aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, count=1)


@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
def test_service_check_unsealed_ok_all_tags(aggregator, dd_run_check, global_tags, use_openmetrics, vault_api):
    instance = {'use_openmetrics': use_openmetrics}
    instance.update(INSTANCES['main'])
    c = Vault(Vault.CHECK_NAME, {}, [instance])

    dd_run_check(c)

    expected_tags = [
        'is_leader:true',
        'vault_cluster:vault-cluster-f5f44063',
        'vault_version:0.10.2',
    ]
    if not use_openmetrics:
        expected_tags.append('cluster_name:vault-cluster-f5f44063')
    expected_tags.extend(global_tags)
    aggregator.assert_service_check(Vault.SERVICE_CHECK_UNSEALED, status=Vault.OK, tags=expected_tags, count=1)


@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
def test_service_check_unsealed_fail(aggregator, dd_run_check, use_openmetrics, vault_api):
    instance = {'use_openmetrics': use_openmetrics}
    instance.update(INSTANCES['main'])
    c = Vault(Vault.CHECK_NAME, {}, [instance])

    vault_api(HEALTH_URL, json_data={**HEALTH_DATA, 'initialized': False, 'sealed': True}, status_code=503)
    dd_run_check(c)

    aggregator.assert_service_check(Vault.SERVICE_CHECK_UNSEALED, status=Vault.CRITICAL, count=1)


@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
def test_service_check_initialized_ok_all_tags(aggregator, dd_run_check, global_tags, use_openmetrics, vault_api):
    instance = {'use_openmetrics': use_openmetrics}
    instance.update(INSTANCES['main'])
    c = Vault(Vault.CHECK_NAME, {}, [instance])

    dd_run_check(c)

    expected_tags = [
        'is_leader:true',
        'vault_cluster:vault-cluster-f5f44063',
        'vault_version:0.10.2',
    ]
    if not use_openmetrics:
        expected_tags.append('cluster_name:vault-cluster-f5f44063')
    expected_tags.extend(global_tags)
    aggregator.assert_service_check(Vault.SERVICE_CHECK_INITIALIZED, status=Vault.OK, tags=expected_tags, count=1)


@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
def test_service_check_initialized_fail(aggregator, dd_run_check, use_openmetrics, vault_api):
    instance = {'use_openmetrics': use_openmetrics}
    instance.update(INSTANCES['main'])
    c = Vault(Vault.CHECK_NAME, {}, [instance])

    vault_api(HEALTH_URL, json_data={**HEALTH_DATA, 'initialized': False}, status_code=501)
    dd_run_check(c)

    aggregator.assert_service_check(Vault.SERVICE_CHECK_INITIALIZED, status=Vault.CRITICAL, count=1)


def test_disable_legacy_cluster_tag(aggregator, dd_run_check, global_tags, vault_api):
    instance = {'disable_legacy_cluster_tag': True, 'use_openmetrics': False}
    instance.update(INSTANCES['main'])
    c = Vault(Vault.CHECK_NAME, {}, [instance])

    dd_run_check(c)

    expected_tags = [
        'is_leader:true',
        'vault_cluster:vault-cluster-f5f44063',
        'vault_version:0.10.2',
    ]
    expected_tags.extend(global_tags)
    aggregator.assert_service_check(Vault.SERVICE_CHECK_INITIALIZED, status=Vault.OK, tags=expected_tags, count=1)


SECONDARY_HEALTH_DATA = {
    **HEALTH_DATA,
    'initialized': False,
    'replication_dr_mode': 'secondary',
    'replication_performance_mode': 'primary',
    'standby': True,
    'performance_standby': False,
}


@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
def test_replication_dr_mode(aggregator, dd_run_check, use_openmetrics, vault_api):
    instance = {'use_openmetrics': use_openmetrics}
    instance.update(INSTANCES['main'])
    c = Vault(Vault.CHECK_NAME, {}, [instance])
    c.log.debug = mock.MagicMock()

    vault_api(HEALTH_URL, json_data=SECONDARY_HEALTH_DATA)
    dd_run_check(c)
    c.log.debug.assert_called_with(
        "Detected vault in replication DR secondary mode, skipping Prometheus metric collection."
    )
    aggregator.assert_metric('vault.is_leader', 1)
    aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1)
    assert_all_metrics(aggregator)


@pytest.mark.parametrize('use_openmetrics', [True, False], indirect=True)
def test_replication_dr_mode_collect_secondary(aggregator, dd_run_check, use_openmetrics, vault_api):
    instance = {'use_openmetrics': use_openmetrics, 'collect_secondary_dr': True}
    instance.update(INSTANCES['main'])
    c = Vault(Vault.CHECK_NAME, {}, [instance])
    c.log.debug = mock.MagicMock()

    metric_collection = 'OpenMetrics' if use_openmetrics else 'Prometheus'

    vault_api(HEALTH_URL, json_data=SECONDARY_HEALTH_DATA)
    dd_run_check(c)
    c.log.debug.assert_called_with(
        "Detected vault in replication DR secondary mode but also detected that "
        "`collect_secondary_dr` is enabled, %s metric collection will still occur." % metric_collection
    )
    aggregator.assert_metric('vault.is_leader', 1)
    aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1)
    assert_all_metrics(aggregator)


@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
def test_replication_dr_mode_changed(aggregator, dd_run_check, use_openmetrics, vault_api):
    instance = {'use_openmetrics': use_openmetrics}
    instance.update(INSTANCES['main'])
    c = Vault(Vault.CHECK_NAME, {}, [instance])
    c.log.debug = mock.MagicMock()

    vault_api(HEALTH_URL, json_data={**SECONDARY_HEALTH_DATA, 'replication_dr_mode': 'primary'}, once=True)
    vault_api(HEALTH_URL, json_data=SECONDARY_HEALTH_DATA)

    dd_run_check(c)
    assert not c._skip_dr_metric_collection
    aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1)
    aggregator.assert_metric('vault.is_leader', 1)
    assert_all_metrics(aggregator)
    aggregator.reset()

    dd_run_check(c)
    c.log.debug.assert_called_with(
        "Detected vault in replication DR secondary mode, skipping Prometheus metric collection."
    )
    assert c._skip_dr_metric_collection
    aggregator.assert_metric('vault.is_leader', 1)
    aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1)
    assert_all_metrics(aggregator)


@pytest.mark.parametrize("cluster", [True, False])
@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
def test_event_leader_change(aggregator, dd_run_check, cluster, use_openmetrics, vault_api):
    instance = {'use_openmetrics': use_openmetrics}
    instance.update(INSTANCES['main'])
    c = Vault(Vault.CHECK_NAME, {}, [instance])
    if cluster:
        c._previous_leader = Leader('', 'foo')
        next_leader = Leader('', 'bar')
    else:
        c._previous_leader = Leader('foo', '')
        next_leader = Leader('bar', '')

    vault_api(
        LEADER_URL,
        json_data={
            'ha_enabled': False,
            'is_self': True,
            'leader_address': next_leader.leader_addr,
            'leader_cluster_address': next_leader.leader_cluster_addr,
        },
    )
    dd_run_check(c)

    assert len(aggregator.events) > 0

    event = aggregator.events[0]
    assert event['event_type'] == c.EVENT_LEADER_CHANGE
    assert event['msg_title'] == 'Leader change'
    if cluster:
        assert event['msg_text'] == 'Leader cluster address changed from `foo` to `bar`.'
    else:
        assert event['msg_text'] == 'Leader address changed from `foo` to `bar`.'
    assert event['alert_type'] == 'info'
    assert event['source_type_name'] == c.CHECK_NAME
    assert event['host'] == c.hostname
    assert 'is_leader:true' in event['tags']
    assert c._previous_leader == next_leader


@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
def test_leader_change_not_self(aggregator, dd_run_check, use_openmetrics, vault_api):
    """The agent should only submit a leader change event when the monitored vault is the leader."""
    instance = {'use_openmetrics': use_openmetrics}
    instance.update(INSTANCES['main'])
    c = Vault(Vault.CHECK_NAME, {}, [instance])
    c._previous_leader = Leader('foo', '')

    vault_api(
        LEADER_URL,
        json_data={'ha_enabled': False, 'is_self': False, 'leader_address': 'bar', 'leader_cluster_address': ''},
    )
    dd_run_check(c)

    assert len(aggregator.events) == 0


@pytest.mark.parametrize('is_self, expected', [(True, 1), (False, 0)])
@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
def test_is_leader_metric(aggregator, dd_run_check, use_openmetrics, vault_api, is_self, expected):
    instance = {'use_openmetrics': use_openmetrics}
    instance.update(INSTANCES['main'])
    c = Vault(Vault.CHECK_NAME, {}, [instance])

    vault_api(
        LEADER_URL,
        json_data={'ha_enabled': False, 'is_self': is_self, 'leader_address': 'bar', 'leader_cluster_address': ''},
    )
    dd_run_check(c)

    aggregator.assert_metric('vault.is_leader', expected)


@pytest.mark.parametrize('status_code', [200, 429, 472, 473, 501, 503])
@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
def test_sys_health_non_standard_status_codes(aggregator, dd_run_check, status_code, use_openmetrics, vault_api):
    instance = {'use_openmetrics': use_openmetrics}
    instance.update(INSTANCES['main'])
    c = Vault(Vault.CHECK_NAME, {}, [instance])

    vault_api(
        HEALTH_URL,
        json_data={**HEALTH_DATA, 'initialized': False, 'standby': True, 'performance_standby': False},
        status_code=status_code,
    )
    dd_run_check(c)

    aggregator.assert_metric('vault.is_leader', 1)
    assert_all_metrics(aggregator)


@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
def test_sys_leader_non_standard_status_codes(aggregator, dd_run_check, use_openmetrics, vault_api):
    instance = {'use_openmetrics': use_openmetrics}
    instance.update(INSTANCES['main'])
    c = Vault(Vault.CHECK_NAME, {}, [instance])

    vault_api(LEADER_URL, json_data={'errors': ["Vault is sealed"]}, status_code=503)
    dd_run_check(c)

    aggregator.assert_metric('vault.is_leader', count=0)


def test_route_transform(aggregator, no_token_instance, global_tags, fake_http_response):
    no_token_instance['use_openmetrics'] = False
    c = Vault(Vault.CHECK_NAME, {}, [no_token_instance])

    c.parse_config()

    fake_http_response(METRICS_URL, read_fixture('route_transform_metrics.txt'))

    c.process(c._scraper_config, c._metric_transformers)

    for quantile in [0.5, 0.9, 0.99]:
        quantile_tag = 'quantile:{}'.format(quantile)
        aggregator.assert_metric('vault.vault.route.rollback.sys.quantile', tags=global_tags + [quantile_tag])
        aggregator.assert_metric('vault.route.rollback.quantile', tags=global_tags + [quantile_tag, 'mountpoint:sys'])
        aggregator.assert_metric('vault.route.rollback.quantile', tags=global_tags + [quantile_tag, 'mountpoint:sys'])
        aggregator.assert_metric('vault.route.create.quantile', tags=global_tags + [quantile_tag, 'mountpoint:foobar'])

    aggregator.assert_metric('vault.vault.route.rollback.sys.sum', tags=global_tags)
    aggregator.assert_metric('vault.vault.route.rollback.sys.count', tags=global_tags)
    aggregator.assert_metric('vault.route.rollback.sum', tags=global_tags + ['mountpoint:sys'])
    aggregator.assert_metric('vault.route.rollback.count', tags=global_tags + ['mountpoint:sys'])
    aggregator.assert_metric('vault.route.create.sum', tags=global_tags + ['mountpoint:foobar'])
    aggregator.assert_metric('vault.route.create.count', tags=global_tags + ['mountpoint:foobar'])

    aggregator.assert_all_metrics_covered()
    aggregator.assert_no_duplicate_metrics()


def test_wal_merkle_metrics(aggregator, token_instance, global_tags, fake_http_response):
    c = Vault(Vault.CHECK_NAME, {}, [token_instance])
    c.parse_config()
    fake_http_response(METRICS_URL, read_fixture('merkle_wal_metrics.txt'))

    c.process(c._scraper_config, c._metric_transformers)

    for metric in MERKLE_WAL_METRICS:
        if metric in MERKLE_WAL_QUANTILES:
            for quantile in [0.5, 0.9, 0.99]:
                quantile_tag = 'quantile:{}'.format(quantile)
                aggregator.assert_metric('{}.quantile'.format(metric), tags=global_tags + [quantile_tag])
        aggregator.assert_metric('{}.sum'.format(metric), tags=global_tags)
        aggregator.assert_metric('{}.count'.format(metric), tags=global_tags)

    aggregator.assert_all_metrics_covered()


def test_token_renewal_on_forbidden(aggregator, dd_run_check, token_instance, global_tags, vault_api):
    token_instance['use_openmetrics'] = False
    c = Vault(Vault.CHECK_NAME, {}, [token_instance])
    # The check recognizes a forbidden scrape by the error message `raise_for_status` produces.
    vault_api(
        METRICS_URL,
        status_code=403,
        status_error=HTTPClientStatusError(f'403 Client Error: Forbidden for url: {METRICS_URL}'),
    )

    dd_run_check(c)

    aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.WARNING, count=1, tags=global_tags)
    aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, count=0)


@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
def test_x_vault_request_header_is_set(token_instance, dd_run_check, use_openmetrics, vault_api, fake_http):
    token_instance['use_openmetrics'] = use_openmetrics
    vault_api(METRICS_URL, read_fixture('route_transform_metrics.txt'))

    c = Vault(Vault.CHECK_NAME, {}, [token_instance])
    dd_run_check(c)

    assert fake_http.requests
    assert c.http.get_header('X-Vault-Request') == 'true'
    if use_openmetrics:
        # The fake records the scraper configuration instead of applying its headers to the client.
        (scraper_client,) = [
            client for client in fake_http.created_clients if 'openmetrics_endpoint' in client.instance
        ]
        assert scraper_client.instance['headers']['X-Vault-Request'] == 'true'
    else:
        assert c.get_http_handler(c._scraper_config).get_header('X-Vault-Request') == 'true'
