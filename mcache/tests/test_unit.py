# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.mcache import Memcache
from datadog_checks.mcache.mcache import BadResponseError

from .common import HOST, PORT, SERVICE_CHECK

pytestmark = pytest.mark.unit


class FakeMemcachedClient:
    def __init__(self, stats_by_key):
        self.stats_by_key = stats_by_key
        self.calls = []

    def stats(self, key=None):
        self.calls.append(key)
        return self.stats_by_key[key]

    def disconnect_all(self):
        pass


class RaisingMemcachedClient:
    def stats(self, key=None):
        raise AssertionError('malformed binary response')

    def disconnect_all(self):
        pass


def test_default_port_is_11211():
    # Kills the core/NumberReplacer mutants at mcache.py:24 (DEFAULT_PORT 11211 -> other values).
    assert Memcache.DEFAULT_PORT == 11211


def test_process_response_raises_on_empty_response(check):
    # Kills the core/ReplaceComparisonOperator and core/NumberReplacer mutants at mcache.py:111 (len(response) != 1).
    with pytest.raises(BadResponseError):
        check._process_response({})


def test_process_response_raises_on_multiple_entries(check):
    # Kills the core/ReplaceComparisonOperator mutants at mcache.py:111 (len(response) != 1 -> < / <= / >=).
    with pytest.raises(BadResponseError):
        check._process_response({'a': {'x': b'1'}, 'b': {'y': b'2'}})


def test_process_response_returns_stats_for_single_entry(check):
    # Kills the core/AddNot mutant at mcache.py:111 (len(response) != 1 -> len(response) == 1 branch inverted).
    stats = check._process_response({'127.0.0.1:11211': {'total_items': b'5'}})
    assert stats == {'total_items': b'5'}


def test_process_response_sets_version_metadata_when_present(check, datadog_agent):
    # Kills the core/AddNot mutant at mcache.py:118 ('version' in stats -> 'version' not in stats).
    check._process_response({'127.0.0.1:11211': {'version': b'1.6.21'}})
    datadog_agent.assert_metadata(check.check_id, {'version.raw': '1.6.21'})


def test_process_response_skips_metadata_when_version_missing(check, datadog_agent):
    # Kills the core/AddNot mutant at mcache.py:118 ('version' in stats -> 'version' not in stats).
    check._process_response({'127.0.0.1:11211': {'total_items': b'5'}})
    datadog_agent.assert_metadata_count(0)


def test_get_metrics_emits_gauges_and_rates_and_not_the_other_type(check, aggregator):
    # Kills the core/ZeroIterationForLoop mutant at mcache.py:127 and the core/AddNot mutants
    # at mcache.py:129 and mcache.py:135 (metric in self.GAUGES / self.RATES checks inverted).
    stats = {'total_items': b'5', 'get_hits': b'2', 'cmd_get': b'3'}
    check._get_metrics(FakeMemcachedClient({None: {'127.0.0.1:11211': stats}}), ['foo:bar'])
    aggregator.assert_metric('memcache.total_items', value=5, tags=['foo:bar'])
    aggregator.assert_metric('memcache.get_hits_rate', value=2, tags=['foo:bar'])
    assert aggregator.metrics('memcache.total_items_rate') == []
    assert aggregator.metrics('memcache.get_hits') == []


def test_get_metrics_computes_get_hit_percent(check, aggregator):
    # Kills the core/ReplaceBinaryOperator mutants at mcache.py:148 (100.0 * get_hits / cmd_get).
    stats = {'get_hits': b'2', 'cmd_get': b'3'}
    check._get_metrics(FakeMemcachedClient({None: {'a': stats}}), ['foo:bar'])
    aggregator.assert_metric('memcache.get_hit_percent', value=100.0 * 2 / 3, tags=['foo:bar'])


def test_get_metrics_computes_get_hit_percent_when_cmd_get_is_negative(check, aggregator):
    # Kills the core/ReplaceComparisonOperator mutants at mcache.py:147 (float(cmd_get) != 0 -> > / >=).
    stats = {'get_hits': b'2', 'cmd_get': b'-3'}
    check._get_metrics(FakeMemcachedClient({None: {'a': stats}}), ['foo:bar'])
    aggregator.assert_metric('memcache.get_hit_percent', value=100.0 * 2 / -3, tags=['foo:bar'])


def test_get_metrics_skips_get_hit_percent_when_cmd_get_is_zero(check, aggregator):
    # Kills the core/ReplaceComparisonOperator mutants at mcache.py:147 (float(cmd_get) != 0 -> == / < / <=).
    stats = {'get_hits': b'2', 'cmd_get': b'0'}
    check._get_metrics(FakeMemcachedClient({None: {'a': stats}}), ['foo:bar'])
    assert aggregator.metrics('memcache.get_hit_percent') == []


def test_get_metrics_skips_get_hit_percent_when_get_hits_missing(check, aggregator):
    # Kills the core/AddNot and core/ReplaceAndWithOr mutants at mcache.py:147 (get_hits and cmd_get and ...).
    stats = {'cmd_get': b'3'}
    check._get_metrics(FakeMemcachedClient({None: {'a': stats}}), ['foo:bar'])
    assert aggregator.metrics('memcache.get_hit_percent') == []


def test_get_metrics_skips_get_hit_percent_when_cmd_get_missing(check, aggregator):
    # Kills the core/AddNot and core/ReplaceAndWithOr mutants at mcache.py:147 (get_hits and cmd_get and ...).
    stats = {'get_hits': b'2'}
    check._get_metrics(FakeMemcachedClient({None: {'a': stats}}), ['foo:bar'])
    assert aggregator.metrics('memcache.get_hit_percent') == []


def test_get_metrics_computes_fill_percent(check, aggregator):
    # Kills the core/ReplaceBinaryOperator mutants at mcache.py:156 (100.0 * bytes / limit_maxbytes).
    stats = {'bytes': b'2', 'limit_maxbytes': b'3'}
    check._get_metrics(FakeMemcachedClient({None: {'a': stats}}), ['foo:bar'])
    aggregator.assert_metric('memcache.fill_percent', value=100.0 * 2 / 3, tags=['foo:bar'])


def test_get_metrics_computes_fill_percent_when_limit_maxbytes_is_negative(check, aggregator):
    # Kills the core/ReplaceComparisonOperator mutants at mcache.py:155 (float(limit_maxbytes) != 0 -> > / >=).
    stats = {'bytes': b'2', 'limit_maxbytes': b'-3'}
    check._get_metrics(FakeMemcachedClient({None: {'a': stats}}), ['foo:bar'])
    aggregator.assert_metric('memcache.fill_percent', value=100.0 * 2 / -3, tags=['foo:bar'])


def test_get_metrics_skips_fill_percent_when_limit_maxbytes_is_zero(check, aggregator):
    # Kills the core/ReplaceComparisonOperator mutants at mcache.py:155 (float(limit_maxbytes) != 0 -> == / < / <=).
    stats = {'bytes': b'2', 'limit_maxbytes': b'0'}
    check._get_metrics(FakeMemcachedClient({None: {'a': stats}}), ['foo:bar'])
    assert aggregator.metrics('memcache.fill_percent') == []


def test_get_metrics_skips_fill_percent_when_bytes_missing(check, aggregator):
    # Kills the core/AddNot and core/ReplaceAndWithOr mutants at mcache.py:155 (bytes and limit_maxbytes and ...).
    stats = {'limit_maxbytes': b'3'}
    check._get_metrics(FakeMemcachedClient({None: {'a': stats}}), ['foo:bar'])
    assert aggregator.metrics('memcache.fill_percent') == []


def test_get_metrics_skips_fill_percent_when_limit_maxbytes_missing(check, aggregator):
    # Kills the core/AddNot and core/ReplaceAndWithOr mutants at mcache.py:155 (bytes and limit_maxbytes and ...).
    stats = {'bytes': b'2'}
    check._get_metrics(FakeMemcachedClient({None: {'a': stats}}), ['foo:bar'])
    assert aggregator.metrics('memcache.fill_percent') == []


def test_get_metrics_computes_avg_item_size(check, aggregator):
    # Kills the core/ReplaceBinaryOperator mutants at mcache.py:164 (bytes / curr_items).
    stats = {'bytes': b'2', 'curr_items': b'3'}
    check._get_metrics(FakeMemcachedClient({None: {'a': stats}}), ['foo:bar'])
    aggregator.assert_metric('memcache.avg_item_size', value=2 / 3, tags=['foo:bar'])


def test_get_metrics_computes_avg_item_size_when_curr_items_is_negative(check, aggregator):
    # Kills the core/ReplaceComparisonOperator mutants at mcache.py:163 (float(curr_items) != 0 -> > / >=).
    stats = {'bytes': b'2', 'curr_items': b'-3'}
    check._get_metrics(FakeMemcachedClient({None: {'a': stats}}), ['foo:bar'])
    aggregator.assert_metric('memcache.avg_item_size', value=2 / -3, tags=['foo:bar'])


def test_get_metrics_skips_avg_item_size_when_curr_items_is_zero(check, aggregator):
    # Kills the core/ReplaceComparisonOperator mutants at mcache.py:163 (float(curr_items) != 0 -> == / < / <=).
    stats = {'bytes': b'2', 'curr_items': b'0'}
    check._get_metrics(FakeMemcachedClient({None: {'a': stats}}), ['foo:bar'])
    assert aggregator.metrics('memcache.avg_item_size') == []


def test_get_metrics_skips_avg_item_size_when_bytes_missing(check, aggregator):
    # Kills the core/AddNot and core/ReplaceAndWithOr mutants at mcache.py:163 (bytes and curr_items and ...).
    stats = {'curr_items': b'3'}
    check._get_metrics(FakeMemcachedClient({None: {'a': stats}}), ['foo:bar'])
    assert aggregator.metrics('memcache.avg_item_size') == []


def test_get_metrics_skips_avg_item_size_when_curr_items_missing(check, aggregator):
    # Kills the core/AddNot and core/ReplaceAndWithOr mutants at mcache.py:163 (bytes and curr_items and ...).
    stats = {'bytes': b'2'}
    check._get_metrics(FakeMemcachedClient({None: {'a': stats}}), ['foo:bar'])
    assert aggregator.metrics('memcache.avg_item_size') == []


def test_is_ipv6_returns_true_for_valid_address(check):
    # Kills the core/ReplaceTrueWithFalse mutant at mcache.py:182 (return True -> return False).
    assert check._is_ipv6('::1') is True


def test_is_ipv6_returns_false_for_invalid_address(check):
    assert check._is_ipv6('127.0.0.1') is False


def test_get_optional_metrics_iterates_every_optional_stat(check, aggregator, monkeypatch):
    # Kills the core/ZeroIterationForLoop mutant at mcache.py:187 (for arg, metrics_args in OPTIONAL_STATS.items()).
    monkeypatch.setattr(
        check,
        'OPTIONAL_STATS',
        {
            'items': [list(Memcache.ITEMS_RATES), list(Memcache.ITEMS_GAUGES), None],
            'slabs': [list(Memcache.SLABS_RATES), list(Memcache.SLABS_GAUGES), None],
        },
    )
    fake_client = FakeMemcachedClient({'items': {'a': {'number': b'4'}}, 'slabs': {'a': {'chunk_size': b'96'}}})
    check._get_optional_metrics(fake_client, ['foo:bar'])
    aggregator.assert_metric('memcache.items.number', value=4, tags=['foo:bar'])
    aggregator.assert_metric('memcache.slabs.chunk_size', value=96, tags=['foo:bar'])


def test_get_optional_metrics_processes_all_when_options_empty(check, aggregator, monkeypatch):
    # Kills the core/ReplaceUnaryOperator_Delete_Not mutant at mcache.py:188 (not options or options.get(arg, False)).
    monkeypatch.setattr(
        check,
        'OPTIONAL_STATS',
        {
            'items': [list(Memcache.ITEMS_RATES), list(Memcache.ITEMS_GAUGES), None],
            'slabs': [list(Memcache.SLABS_RATES), list(Memcache.SLABS_GAUGES), None],
        },
    )
    fake_client = FakeMemcachedClient({'items': {'a': {'number': b'4'}}, 'slabs': {'a': {'chunk_size': b'96'}}})
    check._get_optional_metrics(fake_client, ['foo:bar'], options={})
    aggregator.assert_metric('memcache.items.number', value=4, tags=['foo:bar'])
    aggregator.assert_metric('memcache.slabs.chunk_size', value=96, tags=['foo:bar'])


def test_get_optional_metrics_options_filters_per_arg(check, aggregator, monkeypatch):
    # Kills the core/ReplaceFalseWithTrue and core/ReplaceOrWithAnd mutants at mcache.py:188
    # (options.get(arg, False) default, and "not options or options.get(...)").
    monkeypatch.setattr(
        check,
        'OPTIONAL_STATS',
        {
            'items': [list(Memcache.ITEMS_RATES), list(Memcache.ITEMS_GAUGES), None],
            'slabs': [list(Memcache.SLABS_RATES), list(Memcache.SLABS_GAUGES), None],
        },
    )
    fake_client = FakeMemcachedClient({'items': {'a': {'number': b'4'}}, 'slabs': {'a': {'chunk_size': b'96'}}})
    check._get_optional_metrics(fake_client, ['foo:bar'], options={'items': True})
    aggregator.assert_metric('memcache.items.number', value=4, tags=['foo:bar'])
    assert aggregator.metrics('memcache.slabs.chunk_size') == []


def test_get_optional_metrics_uses_correct_rate_gauge_and_handler_slots(check, aggregator, monkeypatch):
    # Kills the core/NumberReplacer index mutants at mcache.py:190-192 (metrics_args[0]/[1]/[2] swapped)
    # and the core/AddNot mutant at mcache.py:200 (if optional_fn: -> if not optional_fn:).
    def handler(metric, val):
        return metric, ['handled:yes'], val

    monkeypatch.setattr(check, 'OPTIONAL_STATS', {'items': [['a_rate'], ['a_gauge'], handler], 'slabs': [[], [], None]})
    fake_client = FakeMemcachedClient({'items': {'srv': {'a_rate': b'2', 'a_gauge': b'3'}}, 'slabs': {'srv': {}}})
    check._get_optional_metrics(fake_client, ['foo:bar'], options={'items': True})
    aggregator.assert_metric('memcache.items.a_rate_rate', value=2, tags=['foo:bar', 'handled:yes'])
    aggregator.assert_metric('memcache.items.a_gauge', value=3, tags=['foo:bar', 'handled:yes'])
    assert aggregator.metrics('memcache.items.a_rate') == []
    assert aggregator.metrics('memcache.items.a_gauge_rate') == []


def test_get_optional_metrics_logs_warning_on_malformed_stats_response(check, aggregator, monkeypatch):
    # Kills the core/ExceptionReplacer mutant at mcache.py:210 (except BadResponseError -> except SomeOtherError).
    monkeypatch.setattr(
        check,
        'OPTIONAL_STATS',
        {
            'items': [list(Memcache.ITEMS_RATES), list(Memcache.ITEMS_GAUGES), None],
            'slabs': [list(Memcache.SLABS_RATES), list(Memcache.SLABS_GAUGES), None],
        },
    )
    fake_client = FakeMemcachedClient({'items': {}, 'slabs': {'a': {'chunk_size': b'96'}}})
    check._get_optional_metrics(fake_client, ['foo:bar'])
    assert aggregator.metrics('memcache.items.number') == []
    aggregator.assert_metric('memcache.slabs.chunk_size', value=96, tags=['foo:bar'])


def test_get_optional_metrics_logs_exception_on_handler_failure(check, aggregator, monkeypatch):
    # Kills the core/ExceptionReplacer mutant at mcache.py:216 (except Exception -> except SomeOtherError).
    def broken_handler(metric, val):
        raise ValueError('boom')

    monkeypatch.setattr(
        check,
        'OPTIONAL_STATS',
        {
            'items': [[], [], broken_handler],
            'slabs': [list(Memcache.SLABS_RATES), list(Memcache.SLABS_GAUGES), None],
        },
    )
    fake_client = FakeMemcachedClient({'items': {'a': {'x': b'1'}}, 'slabs': {'a': {'chunk_size': b'96'}}})
    check._get_optional_metrics(fake_client, ['foo:bar'], options={'items': True, 'slabs': True})
    aggregator.assert_metric('memcache.slabs.chunk_size', value=96, tags=['foo:bar'])


def test_get_items_stats_is_declared_as_staticmethod():
    # Kills the core/RemoveDecorator mutant at mcache.py:219 (@staticmethod removed from get_items_stats).
    assert isinstance(Memcache.__dict__['get_items_stats'], staticmethod)


def test_get_items_stats_parses_slab_and_metric_from_key(check):
    # Kills the core/NumberReplacer index mutants at mcache.py:230-231 (itemized_key[1]/[2] swapped).
    metric, tags, value = Memcache.get_items_stats('items:7:number', b'4')
    assert metric == 'number'
    assert tags == ['slab:7']
    assert value == b'4'


def test_get_slabs_stats_is_declared_as_staticmethod():
    # Kills the core/RemoveDecorator mutant at mcache.py:237 (@staticmethod removed from get_slabs_stats).
    assert isinstance(Memcache.__dict__['get_slabs_stats'], staticmethod)


def test_get_slabs_stats_two_segment_key_extracts_slab_and_metric(check):
    # Kills the core/ReplaceComparisonOperator mutants at mcache.py:249 (len(slabbed_key) == 2 -> != / < / <=).
    metric, tags, value = Memcache.get_slabs_stats('7:chunk_size', b'96')
    assert metric == 'chunk_size'
    assert tags == ['slab:7']
    assert value == b'96'


def test_get_slabs_stats_single_segment_key_has_no_slab_tag(check):
    # Kills the core/ReplaceComparisonOperator mutants at mcache.py:249 (len(slabbed_key) == 2 -> != / >= / <=).
    metric, tags, value = Memcache.get_slabs_stats('active_slabs', b'3')
    assert metric == 'active_slabs'
    assert tags == []
    assert value == b'3'


def test_get_slabs_stats_three_segment_key_falls_to_else_branch(check):
    # Kills the core/ReplaceComparisonOperator mutants at mcache.py:249 (len(slabbed_key) == 2 -> >= / <=).
    metric, tags, value = Memcache.get_slabs_stats('1:used_chunks:extra', b'5')
    assert metric == '1'
    assert tags == []
    assert value == b'5'


def test_check_skips_optional_metrics_when_options_absent(check, monkeypatch):
    # Kills the core/AddNot mutant at mcache.py:291 (if options: -> if not options:).
    fake_client = FakeMemcachedClient({None: {'127.0.0.1:11211': {'get_hits': b'2', 'cmd_get': b'3'}}})
    monkeypatch.setattr('datadog_checks.mcache.mcache.bmemcached.Client', lambda *a, **k: fake_client)
    check.check({'url': HOST, 'port': PORT})
    assert fake_client.calls == [None]


def test_check_wires_items_and_slabs_handlers_when_options_present(check, aggregator, monkeypatch):
    # Kills the core/NumberReplacer index mutants at mcache.py:293-294 (OPTIONAL_STATS[...][2] index swapped).
    monkeypatch.setattr(
        check,
        'OPTIONAL_STATS',
        {
            'items': [list(Memcache.ITEMS_RATES), list(Memcache.ITEMS_GAUGES), None],
            'slabs': [list(Memcache.SLABS_RATES), list(Memcache.SLABS_GAUGES), None],
        },
    )
    fake_client = FakeMemcachedClient(
        {
            None: {'127.0.0.1:11211': {'get_hits': b'2', 'cmd_get': b'3'}},
            'items': {'127.0.0.1:11211': {'items:1:number': b'4'}},
            'slabs': {'127.0.0.1:11211': {'1:chunk_size': b'96'}},
        }
    )
    monkeypatch.setattr('datadog_checks.mcache.mcache.bmemcached.Client', lambda *a, **k: fake_client)
    check.check({'url': HOST, 'port': PORT, 'options': {'items': True, 'slabs': True}})
    tags = ['url:{}:{}'.format(HOST, PORT), 'slab:1']
    aggregator.assert_metric('memcache.items.number', value=4, tags=tags)
    aggregator.assert_metric('memcache.slabs.chunk_size', value=96, tags=tags)


def test_check_handles_assertion_error_as_malformed_binary_response(check, aggregator, monkeypatch):
    # Kills the core/ExceptionReplacer mutant at mcache.py:308 (except AssertionError -> except SomeOtherError),
    # and the core/ReplaceBinaryOperator_Mod_Add and _Mod_Mul mutants at mcache.py:284
    # ("host:%s" % server, "port:%s" % port -> "host:%s" + server / "port:%s" * port).
    monkeypatch.setattr('datadog_checks.mcache.mcache.bmemcached.Client', lambda *a, **k: RaisingMemcachedClient())
    check.check({'url': HOST, 'port': PORT})
    sc = aggregator.service_checks(SERVICE_CHECK)[0]
    assert sc.status == check.WARNING
    assert sc.tags == ['host:%s' % HOST, 'port:%s' % PORT]


def test_check_allows_socket_config_without_url(check, monkeypatch):
    # Kills the core/ReplaceUnaryOperator_Delete_Not mutant at mcache.py:265
    # (if not server and not socket: -> if not server and socket:).
    fake_client = FakeMemcachedClient({None: {'127.0.0.1:11211': {'get_hits': b'2', 'cmd_get': b'3'}}})
    monkeypatch.setattr('datadog_checks.mcache.mcache.bmemcached.Client', lambda *a, **k: fake_client)
    check.check({'socket': '/tmp/memcached.sock'})
    assert fake_client.calls == [None]
