# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.mcache import Memcache
from datadog_checks.mcache.mcache import BadResponseError, InvalidConfigError

pytestmark = pytest.mark.unit


def make_check():
    # Inline factory rather than the conftest `check` fixture because
    # mcache/tests/conftest.py imports Docker-only helpers, which makes it
    # unusable in env-agnostic unit tests.
    return Memcache('mcache', None, {}, [{}])


def build_stats_response(**overrides):
    stats = {
        'host:11211': {
            'version': b'1.6.18',
            'curr_items': b'10',
            'cmd_get': b'200',
            'get_hits': b'150',
            'cmd_set': b'50',
            'bytes': b'500',
            'limit_maxbytes': b'1000',
            'curr_connections': b'4',
        }
    }
    stats['host:11211'].update(overrides)
    return stats


def test_default_port_is_11211():
    assert Memcache.DEFAULT_PORT == 11211


def test_source_type_name():
    assert Memcache.SOURCE_TYPE_NAME == 'memcached'


def test_service_check_name():
    assert Memcache.SERVICE_CHECK == 'memcache.can_connect'


def test_gauges_list_contents():
    assert Memcache.GAUGES == [
        "total_items",
        "curr_items",
        "limit_maxbytes",
        "uptime",
        "bytes",
        "curr_connections",
        "max_connections",
        "connection_structures",
        "threads",
        "pointer_size",
    ]


def test_rates_list_contents():
    assert Memcache.RATES == [
        "rusage_user",
        "rusage_system",
        "cmd_get",
        "cmd_set",
        "cmd_flush",
        "get_hits",
        "get_misses",
        "delete_misses",
        "delete_hits",
        "evictions",
        "bytes_read",
        "bytes_written",
        "cas_misses",
        "cas_hits",
        "cas_badval",
        "total_connections",
        "listen_disabled_num",
    ]


def test_items_rates_list_contents():
    assert Memcache.ITEMS_RATES == [
        "evicted",
        "evicted_nonzero",
        "expired_unfetched",
        "evicted_unfetched",
        "outofmemory",
        "tailrepairs",
        "moves_to_cold",
        "moves_to_warm",
        "moves_within_lru",
        "reclaimed",
        "crawler_reclaimed",
        "lrutail_reflocked",
        "direct_reclaims",
    ]


def test_items_gauges_list_contents():
    assert Memcache.ITEMS_GAUGES == [
        "number",
        "number_hot",
        "number_warm",
        "number_cold",
        "number_noexp",
        "age",
        "evicted_time",
    ]


def test_slabs_rates_list_contents():
    assert Memcache.SLABS_RATES == [
        "get_hits",
        "cmd_set",
        "delete_hits",
        "incr_hits",
        "decr_hits",
        "cas_hits",
        "cas_badval",
        "touch_hits",
        "used_chunks",
    ]


def test_slabs_gauges_list_contents():
    assert Memcache.SLABS_GAUGES == [
        "chunk_size",
        "chunks_per_page",
        "total_pages",
        "total_chunks",
        "used_chunks",
        "free_chunks",
        "free_chunks_end",
        "mem_requested",
        "active_slabs",
        "total_malloced",
    ]


def test_optional_stats_keys_and_shape():
    keys = list(Memcache.OPTIONAL_STATS.keys())
    assert keys == ["items", "slabs"]
    items_entry = Memcache.OPTIONAL_STATS["items"]
    slabs_entry = Memcache.OPTIONAL_STATS["slabs"]
    assert items_entry[0] is Memcache.ITEMS_RATES
    assert items_entry[1] is Memcache.ITEMS_GAUGES
    assert slabs_entry[0] is Memcache.SLABS_RATES
    assert slabs_entry[1] is Memcache.SLABS_GAUGES
    assert items_entry[2] is None
    assert slabs_entry[2] is None


def test_process_response_raises_on_more_than_one_host():
    check = make_check()
    with pytest.raises(BadResponseError):
        check._process_response({'host1': {'version': b'1.0'}, 'host2': {'version': b'1.0'}})


def test_process_response_raises_on_zero_hosts():
    check = make_check()
    with pytest.raises(BadResponseError):
        check._process_response({})


def test_process_response_raises_on_empty_stats_for_host():
    check = make_check()
    with pytest.raises(BadResponseError):
        check._process_response({'host:11211': {}})


def test_process_response_sets_version_metadata_when_present():
    check = make_check()
    with mock.patch.object(check, 'set_metadata') as mock_set_metadata:
        stats = check._process_response({'host:11211': {'version': b'1.6.18', 'curr_items': b'5'}})
    mock_set_metadata.assert_called_once_with('version', '1.6.18')
    assert stats == {'version': b'1.6.18', 'curr_items': b'5'}


def test_process_response_skips_version_metadata_when_missing():
    check = make_check()
    with mock.patch.object(check, 'set_metadata') as mock_set_metadata:
        stats = check._process_response({'host:11211': {'curr_items': b'5'}})
    mock_set_metadata.assert_not_called()
    assert stats == {'curr_items': b'5'}


def test_is_ipv6_true_for_ipv6_address():
    check = make_check()
    assert check._is_ipv6('2001:db8::2') is True


def test_is_ipv6_false_for_ipv4_address():
    check = make_check()
    assert check._is_ipv6('127.0.0.1') is False


def test_is_ipv6_false_for_hostname():
    check = make_check()
    assert check._is_ipv6('localhost') is False


def test_get_items_stats_parses_items_key():
    metric, tags, value = Memcache.get_items_stats('items:7:evicted', b'42')
    assert metric == 'evicted'
    assert tags == ['slab:7']
    assert value == b'42'


def test_get_items_stats_uses_second_field_for_slab_id():
    metric, tags, value = Memcache.get_items_stats('prefix:99:metric_name', 'value')
    assert metric == 'metric_name'
    assert tags == ['slab:99']
    assert value == 'value'


def test_get_slabs_stats_two_part_key_emits_slab_tag():
    metric, tags, value = Memcache.get_slabs_stats('5:chunk_size', b'80')
    assert metric == 'chunk_size'
    assert tags == ['slab:5']
    assert value == b'80'


def test_get_slabs_stats_single_part_key_has_no_tag():
    metric, tags, value = Memcache.get_slabs_stats('active_slabs', b'3')
    assert metric == 'active_slabs'
    assert tags == []
    assert value == b'3'


def test_get_slabs_stats_three_part_key_falls_through_to_no_tag_branch():
    metric, tags, value = Memcache.get_slabs_stats('a:b:c', b'1')
    assert metric == 'a'
    assert tags == []
    assert value == b'1'


def test_get_items_stats_is_callable_on_instance_without_self():
    # @staticmethod means calling via an instance does not bind self.
    # If the decorator is stripped, instance.get_items_stats(key, value) would
    # bind self=instance, key=key, value=missing.
    check = make_check()
    metric, tags, value = check.get_items_stats('items:1:evicted', b'9')
    assert metric == 'evicted'
    assert tags == ['slab:1']
    assert value == b'9'


def test_get_slabs_stats_is_callable_on_instance_without_self():
    check = make_check()
    metric, tags, value = check.get_slabs_stats('2:chunk_size', b'80')
    assert metric == 'chunk_size'
    assert tags == ['slab:2']
    assert value == b'80'


def test_get_metrics_emits_gauges_rates_and_percentages(aggregator):
    check = make_check()
    client = mock.Mock()
    client.stats.return_value = build_stats_response()

    check._get_metrics(client, tags=['url:host:11211'], service_check_tags=['host:host'])

    aggregator.assert_metric('memcache.curr_items', value=10.0, tags=['url:host:11211'], metric_type=aggregator.GAUGE)
    aggregator.assert_metric('memcache.bytes', value=500.0, tags=['url:host:11211'], metric_type=aggregator.GAUGE)
    aggregator.assert_metric('memcache.get_hits_rate', tags=['url:host:11211'], metric_type=aggregator.RATE)
    aggregator.assert_metric('memcache.cmd_get_rate', tags=['url:host:11211'], metric_type=aggregator.RATE)
    aggregator.assert_metric(
        'memcache.get_hit_percent', value=75.0, tags=['url:host:11211'], metric_type=aggregator.GAUGE
    )
    aggregator.assert_metric('memcache.fill_percent', value=50.0, tags=['url:host:11211'], metric_type=aggregator.GAUGE)
    aggregator.assert_metric(
        'memcache.avg_item_size', value=50.0, tags=['url:host:11211'], metric_type=aggregator.GAUGE
    )
    aggregator.assert_service_check(Memcache.SERVICE_CHECK, status=AgentCheck.OK, tags=['host:host'])


def test_get_metrics_skips_get_hit_percent_when_cmd_get_zero(aggregator):
    check = make_check()
    client = mock.Mock()
    client.stats.return_value = build_stats_response(cmd_get=b'0', get_hits=b'5')

    with mock.patch.object(check.log, 'warning') as mock_warning:
        check._get_metrics(client, tags=['t'], service_check_tags=['t'])

    warning_messages = [call.args[0] for call in mock_warning.call_args_list]
    assert any('memcache.get_hit_percent' in msg for msg in warning_messages)
    aggregator.assert_metric('memcache.get_hit_percent', count=0)


def test_get_metrics_skips_fill_percent_when_limit_maxbytes_zero(aggregator):
    check = make_check()
    client = mock.Mock()
    client.stats.return_value = build_stats_response(limit_maxbytes=b'0', bytes=b'5')

    with mock.patch.object(check.log, 'warning') as mock_warning:
        check._get_metrics(client, tags=['t'], service_check_tags=['t'])

    warning_messages = [call.args[0] for call in mock_warning.call_args_list]
    assert any('memcache.fill_percent' in msg for msg in warning_messages)
    aggregator.assert_metric('memcache.fill_percent', count=0)


def test_get_metrics_skips_avg_item_size_when_curr_items_zero(aggregator):
    check = make_check()
    client = mock.Mock()
    client.stats.return_value = build_stats_response(curr_items=b'0', bytes=b'5')

    with mock.patch.object(check.log, 'warning') as mock_warning:
        check._get_metrics(client, tags=['t'], service_check_tags=['t'])

    warning_messages = [call.args[0] for call in mock_warning.call_args_list]
    assert any('memcache.avg_item_size' in msg for msg in warning_messages)
    aggregator.assert_metric('memcache.avg_item_size', count=0)


def test_get_metrics_emits_get_hit_percent_when_cmd_get_negative(aggregator):
    # `float(cmd_get) != 0` is True for negative values; `> 0` would be False.
    # Mutants that flip != to > should be killed by this asymmetry.
    check = make_check()
    client = mock.Mock()
    client.stats.return_value = build_stats_response(cmd_get=b'-2', get_hits=b'1')

    check._get_metrics(client, tags=['url:t'], service_check_tags=['t'])

    aggregator.assert_metric('memcache.get_hit_percent', value=-50.0, tags=['url:t'])


def test_get_metrics_emits_fill_percent_when_limit_maxbytes_negative(aggregator):
    check = make_check()
    client = mock.Mock()
    client.stats.return_value = build_stats_response(bytes=b'1', limit_maxbytes=b'-2')

    check._get_metrics(client, tags=['url:t'], service_check_tags=['t'])

    aggregator.assert_metric('memcache.fill_percent', value=-50.0, tags=['url:t'])


def test_get_metrics_emits_avg_item_size_when_curr_items_negative(aggregator):
    check = make_check()
    client = mock.Mock()
    client.stats.return_value = build_stats_response(bytes=b'1', curr_items=b'-2')

    check._get_metrics(client, tags=['url:t'], service_check_tags=['t'])

    aggregator.assert_metric('memcache.avg_item_size', value=-0.5, tags=['url:t'])


def test_get_metrics_skips_get_hit_percent_when_get_hits_missing(aggregator):
    check = make_check()
    client = mock.Mock()
    stats = build_stats_response()
    del stats['host:11211']['get_hits']
    client.stats.return_value = stats

    check._get_metrics(client, tags=['t'], service_check_tags=['t'])

    aggregator.assert_metric('memcache.get_hit_percent', count=0)


def test_get_metrics_propagates_bad_response_error(aggregator):
    check = make_check()
    client = mock.Mock()
    client.stats.return_value = {}

    with pytest.raises(BadResponseError):
        check._get_metrics(client, tags=['t'], service_check_tags=['t'])


def test_get_metrics_get_hit_percent_uses_true_division(aggregator):
    # cmd_get=3, get_hits=1 → 100.0 * 1 / 3 = 33.333... With // it would be 33.0.
    check = make_check()
    client = mock.Mock()
    client.stats.return_value = build_stats_response(cmd_get=b'3', get_hits=b'1')

    check._get_metrics(client, tags=['url:t'], service_check_tags=['t'])

    aggregator.assert_metric('memcache.get_hit_percent', value=100.0 / 3, tags=['url:t'])


def test_get_metrics_fill_percent_uses_true_division(aggregator):
    # bytes=1, limit=3 → 100.0 * 1 / 3 = 33.333... With // it would be 33.0.
    check = make_check()
    client = mock.Mock()
    client.stats.return_value = build_stats_response(bytes=b'1', limit_maxbytes=b'3')

    check._get_metrics(client, tags=['url:t'], service_check_tags=['t'])

    aggregator.assert_metric('memcache.fill_percent', value=100.0 / 3, tags=['url:t'])


def test_get_metrics_avg_item_size_uses_true_division(aggregator):
    # bytes=10, curr_items=3 → 10 / 3 = 3.333... With // it would be 3.0.
    check = make_check()
    client = mock.Mock()
    client.stats.return_value = build_stats_response(bytes=b'10', curr_items=b'3')

    check._get_metrics(client, tags=['url:t'], service_check_tags=['t'])

    aggregator.assert_metric('memcache.avg_item_size', value=10.0 / 3, tags=['url:t'])


def test_get_optional_metrics_skipped_when_option_disabled(aggregator):
    check = make_check()
    client = mock.Mock()
    client.stats.return_value = {'host': {'evicted': b'1'}}

    check._get_optional_metrics(client, tags=['t'], options={'items': False, 'slabs': False})

    client.stats.assert_not_called()


def test_get_optional_metrics_missing_key_defaults_to_disabled():
    # `options.get(arg, False)` defaults to False, so a missing key behaves
    # like an explicit `False` and the arg is skipped. A mutation flipping the
    # default to True would call stats() for the missing key.
    check = make_check()
    client = mock.Mock()
    client.stats.return_value = {'host': {'evicted': b'1'}}

    check._get_optional_metrics(client, tags=['t'], options={'items': True})

    assert client.stats.call_args_list == [mock.call('items')]


def test_get_optional_metrics_skips_metrics_not_in_gauges_or_rates_list(aggregator):
    # The handlers (get_items_stats) strip "items:N:" and pass through the metric
    # unchanged, so 'unknown_metric_name' is not in ITEMS_GAUGES or ITEMS_RATES.
    # A mutation of `optional_gauges and metric in optional_gauges` to `or` would
    # emit any metric regardless of membership.
    check = make_check()
    client = mock.Mock()
    client.stats.return_value = {'h': {'items:1:unknown_metric_name': b'7'}}

    try:
        Memcache.OPTIONAL_STATS["items"][2] = Memcache.get_items_stats

        check._get_optional_metrics(client, tags=['url:t'], options={'items': True, 'slabs': False})
    finally:
        Memcache.OPTIONAL_STATS["items"][2] = None

    aggregator.assert_metric('memcache.items.unknown_metric_name', count=0)
    aggregator.assert_metric('memcache.items.unknown_metric_name_rate', count=0)


def test_get_optional_metrics_calls_stats_for_each_enabled_arg():
    check = make_check()
    client = mock.Mock()
    client.stats.side_effect = [
        {'h': {'items:1:evicted': b'5', 'items:1:number': b'9'}},
        {'h': {'1:chunk_size': b'80'}},
    ]
    try:
        Memcache.OPTIONAL_STATS["items"][2] = Memcache.get_items_stats
        Memcache.OPTIONAL_STATS["slabs"][2] = Memcache.get_slabs_stats

        check._get_optional_metrics(client, tags=['url:t'], options={'items': True, 'slabs': True})
    finally:
        Memcache.OPTIONAL_STATS["items"][2] = None
        Memcache.OPTIONAL_STATS["slabs"][2] = None

    assert client.stats.call_args_list == [mock.call('items'), mock.call('slabs')]


def test_get_optional_metrics_emits_gauges_and_rates_with_slab_tags(aggregator):
    check = make_check()
    client = mock.Mock()
    client.stats.return_value = {'h': {'items:3:evicted': b'7', 'items:3:number': b'4'}}

    try:
        Memcache.OPTIONAL_STATS["items"][2] = Memcache.get_items_stats

        check._get_optional_metrics(client, tags=['url:t'], options={'items': True, 'slabs': False})
    finally:
        Memcache.OPTIONAL_STATS["items"][2] = None

    aggregator.assert_metric('memcache.items.number', value=4.0, tags=['url:t', 'slab:3'], metric_type=aggregator.GAUGE)
    aggregator.assert_metric('memcache.items.evicted_rate', tags=['url:t', 'slab:3'], metric_type=aggregator.RATE)


def test_get_optional_metrics_swallows_bad_response_error():
    check = make_check()
    client = mock.Mock()
    client.stats.return_value = {}

    with mock.patch.object(check.log, 'warning') as mock_warning:
        check._get_optional_metrics(client, tags=['t'], options={'items': True, 'slabs': False})

    assert mock_warning.called


def test_get_optional_metrics_swallows_unexpected_exception():
    check = make_check()
    client = mock.Mock()
    client.stats.side_effect = RuntimeError('boom')

    with mock.patch.object(check.log, 'exception') as mock_exception:
        check._get_optional_metrics(client, tags=['t'], options={'items': True, 'slabs': False})

    assert mock_exception.called


def test_check_raises_when_url_and_socket_both_missing():
    check = make_check()
    with pytest.raises(InvalidConfigError):
        check.check({})


def test_check_uses_default_port_when_not_set(aggregator):
    check = make_check()
    fake_client = mock.Mock()
    fake_client.stats.return_value = build_stats_response()

    with mock.patch('datadog_checks.mcache.mcache.bmemcached.Client', return_value=fake_client) as mock_client_cls:
        check.check({'url': 'host'})

    mock_client_cls.assert_called_once_with('host:11211', None, None)
    aggregator.assert_metric('memcache.curr_items', tags=['url:host:11211'], metric_type=aggregator.GAUGE)


def test_check_uses_custom_port_when_set(aggregator):
    check = make_check()
    fake_client = mock.Mock()
    fake_client.stats.return_value = build_stats_response()

    with mock.patch('datadog_checks.mcache.mcache.bmemcached.Client', return_value=fake_client) as mock_client_cls:
        check.check({'url': 'host', 'port': 11999})

    mock_client_cls.assert_called_once_with('host:11999', None, None)


def test_check_uses_socket_branch_when_socket_provided(aggregator):
    check = make_check()
    fake_client = mock.Mock()
    fake_client.stats.return_value = build_stats_response()

    with mock.patch('datadog_checks.mcache.mcache.bmemcached.Client', return_value=fake_client) as mock_client_cls:
        check.check({'socket': '/var/run/memcached.sock'})

    mock_client_cls.assert_called_once_with('/var/run/memcached.sock', None, None)
    aggregator.assert_service_check(
        Memcache.SERVICE_CHECK,
        status=AgentCheck.OK,
        tags=['host:unix', 'port:/var/run/memcached.sock'],
    )


def test_check_wraps_ipv6_address_in_brackets(aggregator):
    check = make_check()
    fake_client = mock.Mock()
    fake_client.stats.return_value = build_stats_response()

    with mock.patch('datadog_checks.mcache.mcache.bmemcached.Client', return_value=fake_client) as mock_client_cls:
        check.check({'url': '2001:db8::2', 'port': 11211})

    mock_client_cls.assert_called_once_with('[2001:db8::2]:11211', None, None)


def test_check_passes_username_and_password(aggregator):
    check = make_check()
    fake_client = mock.Mock()
    fake_client.stats.return_value = build_stats_response()

    with mock.patch('datadog_checks.mcache.mcache.bmemcached.Client', return_value=fake_client) as mock_client_cls:
        check.check({'url': 'h', 'port': 1, 'username': 'u', 'password': 'p'})

    mock_client_cls.assert_called_once_with('h:1', 'u', 'p')


def test_check_includes_custom_tags(aggregator):
    check = make_check()
    fake_client = mock.Mock()
    fake_client.stats.return_value = build_stats_response()

    with mock.patch('datadog_checks.mcache.mcache.bmemcached.Client', return_value=fake_client):
        check.check({'url': 'host', 'port': 11211, 'tags': ['foo:bar']})

    aggregator.assert_metric('memcache.curr_items', tags=['url:host:11211', 'foo:bar'], metric_type=aggregator.GAUGE)
    aggregator.assert_service_check(
        Memcache.SERVICE_CHECK,
        status=AgentCheck.OK,
        tags=['host:host', 'port:11211', 'foo:bar'],
    )


def test_check_calls_optional_handlers_when_options_provided(aggregator):
    check = make_check()
    fake_client = mock.Mock()
    fake_client.stats.side_effect = [
        build_stats_response(),
        {'h': {'items:1:evicted': b'2', 'items:1:number': b'9'}},
        {'h': {'1:chunk_size': b'80'}},
    ]

    try:
        with mock.patch('datadog_checks.mcache.mcache.bmemcached.Client', return_value=fake_client):
            check.check({'url': 'host', 'options': {'items': True, 'slabs': True}})

        aggregator.assert_metric('memcache.items.number', value=9.0, tags=['url:host:11211', 'slab:1'])
        aggregator.assert_metric('memcache.slabs.chunk_size', value=80.0, tags=['url:host:11211', 'slab:1'])
    finally:
        Memcache.OPTIONAL_STATS["items"][2] = None
        Memcache.OPTIONAL_STATS["slabs"][2] = None


def test_check_translates_bad_response_into_critical_and_configuration_error(aggregator):
    check = make_check()
    fake_client = mock.Mock()
    fake_client.stats.return_value = {}

    with mock.patch('datadog_checks.mcache.mcache.bmemcached.Client', return_value=fake_client):
        with pytest.raises(ConfigurationError):
            check.check({'url': 'host', 'port': 11211, 'tags': ['foo:bar']})

    aggregator.assert_service_check(
        Memcache.SERVICE_CHECK,
        status=AgentCheck.CRITICAL,
        tags=['host:host', 'port:11211', 'foo:bar'],
    )


def test_check_translates_assertion_error_into_warning_service_check(aggregator):
    check = make_check()
    fake_client = mock.Mock()
    fake_client.stats.side_effect = AssertionError('binary protocol fail')

    with mock.patch('datadog_checks.mcache.mcache.bmemcached.Client', return_value=fake_client):
        check.check({'url': 'host', 'port': 11211})

    aggregator.assert_service_check(
        Memcache.SERVICE_CHECK,
        status=AgentCheck.WARNING,
        tags=['host:host', 'port:11211'],
    )


def test_check_does_not_swallow_non_assertion_non_bad_response_exceptions():
    check = make_check()
    fake_client = mock.Mock()
    fake_client.stats.side_effect = RuntimeError('unexpected')

    with mock.patch('datadog_checks.mcache.mcache.bmemcached.Client', return_value=fake_client):
        with pytest.raises(RuntimeError):
            check.check({'url': 'host', 'port': 11211})


def test_check_disconnects_client_on_happy_path():
    check = make_check()
    fake_client = mock.Mock()
    fake_client.stats.return_value = build_stats_response()

    with mock.patch('datadog_checks.mcache.mcache.bmemcached.Client', return_value=fake_client):
        check.check({'url': 'host'})

    fake_client.disconnect_all.assert_called_once_with()


def test_check_does_not_disconnect_when_assertion_error_path_taken():
    check = make_check()
    fake_client = mock.Mock()
    fake_client.stats.side_effect = AssertionError('boom')

    with mock.patch('datadog_checks.mcache.mcache.bmemcached.Client', return_value=fake_client):
        check.check({'url': 'host'})

    fake_client.disconnect_all.assert_not_called()
