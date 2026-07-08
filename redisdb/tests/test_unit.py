# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import mock
import pytest
import redis
from redis.exceptions import ResponseError

from datadog_checks.base import ConfigurationError
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.redisdb.constants import DEFAULT_MAX_SLOW_ENTRIES, MAX_SLOW_ENTRIES_KEY

pytestmark = pytest.mark.unit


def make_conn(
    info=None,
    keyspace=None,
    config=None,
    client_list=None,
    cluster_info=None,
    command_stats=None,
    slowlog_max_len='128',
    slowlog_entries=None,
):
    """Build a MagicMock redis connection wired up so a full `Redis.check()` run completes end to end.

    `config` maps a `CONFIG GET` key (e.g. "maxclients") to the dict that key should resolve to.
    """
    conn = mock.MagicMock()
    info = {} if info is None else info
    keyspace = [] if keyspace is None else keyspace
    config = {} if config is None else config
    slowlog_entries = [] if slowlog_entries is None else slowlog_entries

    def info_side_effect(*args, **kwargs):
        if args and args[0] == 'keyspace':
            return keyspace
        if args and args[0] == 'commandstats':
            return command_stats or {}
        return info

    def config_get_side_effect(key):
        if key in config:
            return config[key]
        if key == MAX_SLOW_ENTRIES_KEY:
            return {MAX_SLOW_ENTRIES_KEY: slowlog_max_len}
        return {}

    conn.info.side_effect = info_side_effect
    conn.config_get.side_effect = config_get_side_effect
    conn.client_list.return_value = [] if client_list is None else client_list
    conn.cluster.return_value = {} if cluster_info is None else cluster_info
    conn.slowlog_get.return_value = slowlog_entries
    return conn


def test_init(check, redis_instance):
    check = check(redis_instance)
    assert check.connections == {}
    assert check.last_timestamp_seen == 0


def test_check_reuses_cached_connection_across_info_and_slowlog_lookups(check):
    # Kills the core/ReplaceOrWithAnd and comparison-operator mutants on `_get_conn`'s cache-lookup guard
    # (`no_cache or key not in self.connections`) by counting redis.Redis constructions across a single
    # check() run, which calls `_get_conn` twice: once from `_check_db`, once from `_check_slowlog`.
    redis_check = check({'host': 'h', 'port': 1})
    with mock.patch('redis.Redis') as redis_conn:
        redis_check.check(None)
    assert redis_conn.call_count == 1
    assert len(redis_check.connections) == 1


def test_check_disable_connection_cache_reconnects_every_lookup(check):
    # Kills the core/ReplaceOrWithAnd mutant on `_get_conn`'s cache-lookup guard for the no-cache branch.
    redis_check = check({'host': 'h', 'port': 1, 'disable_connection_cache': True})
    with mock.patch('redis.Redis') as redis_conn:
        redis_check.check(None)
    assert redis_conn.call_count == 2


@pytest.mark.parametrize(
    'command_stats, expected_calls_value, expected_usec_per_call_value, command_tag',
    [
        pytest.param(
            {'cmdstat_lpush': {'usec_per_call': 14.00, 'usec': 56, 'calls': 4}},
            4,
            14,
            'command:lpush',
            id='lpush',
        ),
        pytest.param(
            # this is from a real use case in Redis >5.0 where this line can be
            # seen (notice the double ':')
            # cmdstat_host::calls=2,usec=145,usec_per_call=72.50
            {'cmdstat_host': {'usec_per_call': 72.5, 'usec': 145, ':calls': 2}},
            2,
            72.5,
            'command:host',
            id="cmdstat_host with double ':'",
        ),
        pytest.param(
            {'cmdstat_client_list': {'usec_per_call': 3.0, 'usec': 30, 'calls': 10}},
            10,
            3.0,
            'command:client_list',
            id='command name with an underscore',
        ),
        pytest.param(
            {'cmdstat_get': {'usec_per_call': 1.5, 'usec': 15, 'calls': 20}},
            20,
            1.5,
            'command:get',
            id='command alphabetically before host',
        ),
    ],
)
def test_check_command_stats_parses_command_name_and_values(
    check, aggregator, command_stats, expected_calls_value, expected_usec_per_call_value, command_tag
):
    # 'client_list' kills core/NumberReplacer at redisdb.py:484 (`split('_', 1)` -> `split('_', 2)`).
    # 'get' kills core/ReplaceComparisonOperator_NotEq_Gt at redisdb.py:489 (`!= 'host'` -> `> 'host'`).
    redis_check = check({'host': 'h', 'port': 1, 'tags': ['foo:bar'], 'command_stats': True})
    conn = make_conn(command_stats=command_stats)
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)

    base_tags = ['redis_host:h', 'redis_port:1', 'foo:bar']
    aggregator.assert_metric('redis.command.calls', value=expected_calls_value, count=1, tags=base_tags + [command_tag])
    aggregator.assert_metric(
        'redis.command.usec_per_call', value=expected_usec_per_call_value, count=1, tags=base_tags + [command_tag]
    )
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_check_reports_commands_processed_rate_when_present(check, aggregator):
    """The check should send the `redis.net.commands` metric if `total_commands_processed` is present in `c.info`."""
    redis_check = check({'host': 'h', 'port': 1, 'tags': ['test_total_commands_processed']})
    conn = make_conn(info={'total_commands_processed': 1000})
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    aggregator.assert_metric(
        'redis.net.commands', value=1000, tags=['redis_host:h', 'redis_port:1', 'test_total_commands_processed']
    )


def test_check_skips_commands_processed_rate_when_absent(check, aggregator):
    """The check shouldn't send the `redis.net.commands` metric if `total_commands_processed` is absent."""
    redis_check = check({'host': 'h', 'port': 1})
    conn = make_conn(info={})
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    aggregator.assert_metric('redis.net.commands', count=0)


def test_check_all_available_config_options(check, aggregator, redis_instance, dd_run_check):
    """
    The check should should create a connection with the supported config options
    """

    connection_args = {
        'db': 1,
        'username': 'user',
        'password': 'devops-best-friend',
        'socket_timeout': 5,
        'host': 'localhost',
        'port': '6379',
        'unix_socket_path': '/path',
        'ssl': True,
        'ssl_certfile': '/path',
        'ssl_keyfile': '/path',
        'ssl_ca_certs': '/path',
        'ssl_cert_reqs': 0,
        'ssl_check_hostname': True,
        'client_name': 'datadog-agent',
    }
    redis_instance.update(connection_args)

    redis_check = check(redis_instance)
    with mock.patch('redis.Redis') as redis_conn:
        dd_run_check(redis_check)
        assert redis_conn.call_args.kwargs == connection_args


def test_check_slowlog_quiet_failure(check, aggregator):
    """The check should not fail if the slowlog command fails with redis.ResponseError."""
    redis_check = check({'host': 'h', 'port': 1})
    conn = make_conn()
    conn.slowlog_get.side_effect = ResponseError('ERR unknown command `SLOWLOG`')
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    aggregator.assert_metric('redis.slowlog.micros', count=0)


def test_check_slowlog_loud_failure(check):
    """The check should fail if the slowlog command fails for any other reason."""
    redis_check = check({'host': 'h', 'port': 1})
    conn = make_conn()
    conn.slowlog_get.side_effect = RuntimeError('Some other error')
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        with pytest.raises(RuntimeError, match='Some other error'):
            redis_check.check(None)


@pytest.mark.parametrize(
    'cluster_state, expected_state_value',
    [
        pytest.param('ok', 1, id='cluster_state_ok'),
        pytest.param('fail', 0, id='cluster_state_fail'),
        pytest.param('zzz', 0, id='cluster_state_alphabetically_after_ok'),
    ],
)
def test_check_cluster_info_reports_state_and_slot_gauges(check, aggregator, cluster_state, expected_state_value):
    # The 'zzz' case kills the core/ReplaceComparisonOperator_Eq_GtE mutant at redisdb.py:384 (`== 'ok'` -> `>= 'ok'`).
    redis_check = check({'host': 'h', 'port': 1, 'tags': ['foo:bar']})
    conn = make_conn(
        info={'cluster_enabled': 1},
        cluster_info={
            'cluster_state': cluster_state,
            'cluster_slots_assigned': '16384',
            'cluster_slots_ok': '16384',
            'cluster_slots_pfail': '0',
            'cluster_slots_fail': '0',
            'cluster_known_nodes': '6',
            'cluster_size': '3',
            'cluster_current_epoch': '6',
        },
    )
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)

    tags = ['redis_host:h', 'redis_port:1', 'foo:bar']
    conn.cluster.assert_called_once_with('info')
    aggregator.assert_metric('redis.cluster.state', value=expected_state_value, count=1, tags=tags)
    aggregator.assert_metric('redis.cluster.slots_assigned', value=16384, count=1, tags=tags)
    aggregator.assert_metric('redis.cluster.slots_ok', value=16384, count=1, tags=tags)
    aggregator.assert_metric('redis.cluster.slots_pfail', value=0, count=1, tags=tags)
    aggregator.assert_metric('redis.cluster.slots_fail', value=0, count=1, tags=tags)
    aggregator.assert_metric('redis.cluster.known_nodes', value=6, count=1, tags=tags)
    aggregator.assert_metric('redis.cluster.size', value=3, count=1, tags=tags)
    aggregator.assert_metric('redis.cluster.current_epoch', value=6, count=1, tags=tags)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_check_cluster_info_swallows_response_error(check, aggregator):
    """_check_cluster_info should swallow ResponseError (e.g. cluster support disabled)."""
    redis_check = check({'host': 'h', 'port': 1})
    conn = make_conn(info={'cluster_enabled': 1})
    conn.cluster.side_effect = redis.ResponseError('ERR This instance has cluster support disabled')
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    conn.cluster.assert_called_once_with('info')
    aggregator.assert_metric('redis.cluster.state', count=0)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_check_cluster_info_invalid_value(check, aggregator):
    redis_check = check({'host': 'h', 'port': 1, 'tags': ['foo:bar']})
    conn = make_conn(
        info={'cluster_enabled': 1},
        cluster_info={
            'cluster_state': 'ok',
            'cluster_slots_assigned': 'not_a_number',
            'cluster_slots_ok': '16384',
            'cluster_slots_pfail': '0',
            'cluster_slots_fail': '0',
            'cluster_known_nodes': '6',
            'cluster_size': '3',
            'cluster_current_epoch': '6',
        },
    )
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    conn.cluster.assert_called_once_with('info')
    tags = ['redis_host:h', 'redis_port:1', 'foo:bar']
    aggregator.assert_metric('redis.cluster.slots_assigned', count=0)
    aggregator.assert_metric('redis.cluster.slots_ok', value=16384, count=1, tags=tags)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_check_falls_back_to_info_without_section_when_info_all_fails(check, redis_instance, caplog):
    """The check should default to `INFO all` and fall back to `INFO`."""
    redis_check = check(redis_instance)

    def mock_info(*args, **kwargs):
        if kwargs.get('section') == 'all':
            raise redis.ResponseError()
        else:
            return {}

    # Mock the connection object returned by _get_conn
    mock_conn = mock.MagicMock()
    mock_conn.info = mock.MagicMock(side_effect=mock_info)

    with mock.patch.object(redis_check, '_get_conn', return_value=mock_conn):
        with caplog.at_level(logging.DEBUG):
            redis_check.check(None)
    mock_conn.info.assert_has_calls((mock.call(section='all'), mock.call(), mock.call('keyspace')))
    assert any(msg.startswith('`INFO all` command failed, falling back to `INFO`:') for msg in caplog.messages)


def test_init_collect_client_metrics_defaults_to_false(check):
    # Kills the core/ReplaceFalseWithTrue mutant at redisdb.py:42 (`get('collect_client_metrics', False)`).
    redis_check = check({'host': 'h', 'port': 1})
    assert redis_check.collect_client_metrics is False


def test_init_requires_host_and_port_or_unix_socket(check):
    # Kills the core/AddNot mutant at redisdb.py:43 (the missing-host/port ConfigurationError guard).
    with pytest.raises(ConfigurationError):
        check({'host': 'h'})


def test_init_allows_unix_socket_path_without_host_port(check):
    # Kills the core/ReplaceAndWithOr mutant at redisdb.py:43 (`... and "unix_socket_path" not in instance`).
    redis_check = check({'unix_socket_path': '/tmp/redis.sock'})
    assert redis_check.tags == sorted(['redis_host:/tmp/redis.sock', 'redis_port:unix_socket'])


def test_parse_dict_string_finds_value_with_leading_keys(check):
    # Private: `_parse_dict_string` is only ever reached, via the public check(), with subkey in
    # {'keys', 'expires'} and default=-1 (both hardcoded in `_check_db`). Killing all the `k == key`
    # comparison-operator mutants at redisdb.py:54 needs an arbitrary search key, which is unreachable
    # through the public surface.
    # Kills 7 of 8 core/ReplaceComparisonOperator_Eq_* mutants at redisdb.py:54 (`if k == key:`).
    redis_check = check({'host': 'h', 'port': 1})
    assert redis_check._parse_dict_string('aaa=1,zzz=2', 'zzz', -1) == 2


def test_parse_dict_string_finds_value_with_trailing_keys(check):
    # Private: see justification on test_parse_dict_string_finds_value_with_leading_keys above.
    # Kills the remaining core/ReplaceComparisonOperator_Eq_LtE mutant at redisdb.py:54 (`if k == key:`).
    redis_check = check({'host': 'h', 'port': 1})
    assert redis_check._parse_dict_string('zzz=1,mmm=2', 'mmm', -1) == 2


def test_parse_dict_string_returns_string_when_not_int(check):
    # Private: see justification on test_parse_dict_string_finds_value_with_leading_keys above.
    # Kills the core/ExceptionReplacer mutant at redisdb.py:57 (`except ValueError:` -> return the raw string).
    redis_check = check({'host': 'h', 'port': 1})
    assert redis_check._parse_dict_string('key=not_an_int', 'key', -1) == 'not_an_int'


def test_parse_dict_string_returns_default_on_malformed_input(check):
    # Private: see justification on test_parse_dict_string_finds_value_with_leading_keys above.
    # Kills the core/ExceptionReplacer mutant at redisdb.py:60 (`except Exception:` around the rsplit unpack).
    redis_check = check({'host': 'h', 'port': 1})
    assert redis_check._parse_dict_string('malformed', 'key', -1) == -1


def test_check_keys_cached_connection_by_unix_socket_path(check):
    # Kills the core/AddNot mutant at redisdb.py:66 (`if 'unix_socket_path' in instance_config:`) by observing
    # the public `connections` cache key under which redis.Redis connections are stored.
    redis_check = check({'unix_socket_path': '/tmp/redis.sock', 'db': 2})
    with mock.patch('redis.Redis'):
        redis_check.check(None)
    assert list(redis_check.connections.keys()) == [('/tmp/redis.sock', 2)]


def test_check_keys_cached_connection_by_host_port_db(check):
    # Kills the core/AddNot mutant at redisdb.py:66 for instances without a unix_socket_path.
    redis_check = check({'host': 'myhost', 'port': 6379, 'db': 3})
    with mock.patch('redis.Redis'):
        redis_check.check(None)
    assert list(redis_check.connections.keys()) == [('myhost', 6379, 3)]


def test_check_defaults_socket_timeout_to_five_seconds(check):
    # Kills the core/NumberReplacer mutant at redisdb.py:96 (`get('socket_timeout', 5)`).
    redis_check = check({'host': 'h', 'port': 1})
    with mock.patch('redis.Redis') as redis_conn:
        redis_check.check(None)
    assert redis_conn.call_args.kwargs['socket_timeout'] == 5


def test_check_wraps_type_error_from_redis_constructor_with_helpful_message(check):
    # Kills the core/ExceptionReplacer mutant at redisdb.py:102 (`except TypeError:`).
    redis_check = check({'host': 'h', 'port': 1})
    with mock.patch('redis.Redis', side_effect=TypeError('unexpected kwarg')):
        with pytest.raises(Exception, match='pip install redis'):
            redis_check.check(None)


def test_get_tags_uses_unix_socket_port_placeholder(check):
    # Kills the core/AddNot mutant at redisdb.py:109 (`if 'unix_socket_path' in self.instance:`).
    redis_check = check({'unix_socket_path': '/tmp/redis.sock', 'tags': ['extra:tag']})
    assert redis_check.tags == sorted(['redis_host:/tmp/redis.sock', 'redis_port:unix_socket', 'extra:tag'])


def test_get_tags_uses_host_and_port(check):
    # Kills the core/AddNot mutant at redisdb.py:109 for instances without a unix_socket_path.
    redis_check = check({'host': 'myhost', 'port': 1234})
    assert redis_check.tags == ['redis_host:myhost', 'redis_port:1234']


def test_check_service_check_critical_on_ping_value_error(check, aggregator):
    # Kills the core/ExceptionReplacer mutant at redisdb.py:138 (`except ValueError as e:`).
    redis_check = check({'host': 'h', 'port': 1})
    conn = mock.MagicMock()
    conn.ping.side_effect = ValueError('bad value')
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        with pytest.raises(ValueError):
            redis_check.check(None)
    aggregator.assert_service_check('redis.can_connect', status=redis_check.CRITICAL, message='bad value')


def test_check_service_check_critical_on_ping_exception(check, aggregator):
    # Kills the core/ExceptionReplacer mutant at redisdb.py:141 (`except Exception as e:`).
    redis_check = check({'host': 'h', 'port': 1})
    conn = mock.MagicMock()
    conn.ping.side_effect = RuntimeError('connection refused')
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        with pytest.raises(RuntimeError):
            redis_check.check(None)
    aggregator.assert_service_check('redis.can_connect', status=redis_check.CRITICAL, message='connection refused')


def test_check_swallows_config_get_response_error(check, aggregator):
    # Kills the core/ExceptionReplacer mutant at redisdb.py:157 (`except redis.ResponseError:`).
    redis_check = check({'host': 'h', 'port': 1})
    conn = make_conn()
    conn.config_get.side_effect = redis.ResponseError('CONFIG disabled')
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    aggregator.assert_metric('redis.net.maxclients', count=0)


def test_check_persist_and_expires_percentages(check, aggregator):
    # Kills core/ReplaceBinaryOperator_Sub_* (redisdb.py:170) and core/ReplaceBinaryOperator_Mul_*/Div_*
    # (redisdb.py:172-173), plus the ZeroIterationForLoop mutants at redisdb.py:163 and redisdb.py:175.
    redis_check = check({'host': 'h', 'port': 1})
    conn = make_conn(info={'role': 'master', 'db0': {'keys': 10, 'expires': 4}})
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)

    db_tags = ['redis_host:h', 'redis_port:1', 'redis_role:master', 'redis_db:db0']
    aggregator.assert_metric('redis.persist', value=6, tags=db_tags)
    aggregator.assert_metric('redis.persist.percent', value=60.0, tags=db_tags)
    aggregator.assert_metric('redis.expires.percent', value=40.0, tags=db_tags)
    aggregator.assert_metric('redis.keys', value=10, tags=db_tags)
    aggregator.assert_metric('redis.expires', value=4, tags=db_tags)


def test_check_subkey_string_fallback_for_legacy_redis(check, aggregator):
    # Kills the core/NumberReplacer mutant at redisdb.py:182 (`self._parse_dict_string(info[key], subkey, -1)`).
    class LegacyDbInfo(str):
        def __getitem__(self, item):
            if item in ('expires', 'keys'):
                return {'keys': 3, 'expires': 1}[item]
            return super().__getitem__(item)

    redis_check = check({'host': 'h', 'port': 1})
    conn = make_conn(info={'db0': LegacyDbInfo('expires=1')})
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)

    db_tags = ['redis_host:h', 'redis_port:1', 'redis_db:db0']
    aggregator.assert_metric('redis.expires', value=1, tags=db_tags)
    aggregator.assert_metric('redis.keys', value=-1, tags=db_tags)


def test_check_maps_config_get_to_gauge(check, aggregator):
    # Kills the ZeroIterationForLoop mutant at redisdb.py:188 and the core/AddNot mutant at redisdb.py:190.
    redis_check = check({'host': 'h', 'port': 1})
    conn = make_conn(config={'maxclients': {'maxclients': '10000', 'save': '3600 1'}})
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    aggregator.assert_metric('redis.net.maxclients', value=10000.0, count=1)


def test_check_collects_client_metrics_by_name(check, aggregator):
    # Kills core/AddNot at redisdb.py:193, the or/and swap at redisdb.py:197, ZeroIterationForLoop at
    # redisdb.py:198, and core/ReplaceBinaryOperator_Add_Sub at redisdb.py:199.
    redis_check = check({'host': 'h', 'port': 1, 'collect_client_metrics': True})
    conn = make_conn(client_list=[{'name': 'worker'}, {'name': 'worker'}, {'name': ''}])
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)

    aggregator.assert_metric(
        'redis.net.connections', value=2, count=1, tags=['redis_host:h', 'redis_port:1', 'source:worker']
    )
    aggregator.assert_metric(
        'redis.net.connections', value=1, count=1, tags=['redis_host:h', 'redis_port:1', 'source:unknown']
    )


def test_check_swallows_client_list_response_error(check, aggregator):
    # Kills the core/ExceptionReplacer mutant at redisdb.py:200 (`except redis.ResponseError:`).
    redis_check = check({'host': 'h', 'port': 1, 'collect_client_metrics': True})
    conn = make_conn()
    conn.client_list.side_effect = redis.ResponseError('CLIENT disabled')
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    aggregator.assert_metric('redis.net.connections', count=0)


def test_check_triggers_cluster_info_when_enabled(check, aggregator):
    # Kills the core/ReplaceComparisonOperator_Eq_NotEq mutant at redisdb.py:209 (`== 1`).
    redis_check = check({'host': 'h', 'port': 1})
    conn = make_conn(info={'cluster_enabled': 1}, cluster_info={'cluster_state': 'ok'})
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    conn.cluster.assert_called_once_with('info')
    aggregator.assert_metric('redis.cluster.state', value=1)


def test_check_skips_cluster_info_when_disabled(check, aggregator):
    # Kills the core/ReplaceComparisonOperator_Eq_NotEq mutant at redisdb.py:209 for the disabled case.
    redis_check = check({'host': 'h', 'port': 1})
    conn = make_conn(info={'cluster_enabled': 0})
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    conn.cluster.assert_not_called()
    aggregator.assert_metric('redis.cluster.state', count=0)


def test_check_triggers_command_stats_when_enabled(check):
    # Kills the core/AddNot mutant at redisdb.py:211 (`if self.instance.get("command_stats", False):`).
    redis_check = check({'host': 'h', 'port': 1, 'command_stats': True})
    conn = make_conn()
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    assert mock.call('commandstats') in conn.info.call_args_list


def test_check_skips_command_stats_by_default(check):
    # Kills the core/AddNot mutant at redisdb.py:211 for the default (disabled) case.
    redis_check = check({'host': 'h', 'port': 1})
    conn = make_conn()
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    assert mock.call('commandstats') not in conn.info.call_args_list


def test_check_key_lengths_returns_early_when_keys_is_not_a_list(check, aggregator):
    # Kills the core/ReplaceOrWithAnd mutant at redisdb.py:234 (`not isinstance(...) or not key_list`).
    redis_check = check({'host': 'h', 'port': 1, 'keys': 'not_a_list'})
    conn = make_conn()
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    assert mock.call('keyspace') not in conn.info.call_args_list
    aggregator.assert_metric('redis.key.length', count=0)


def test_check_key_lengths_empty_database_warns(check, aggregator):
    # Kills core/AddNot at redisdb.py:242/246/250, core/NumberReplacer at redisdb.py:249, and
    # core/ReplaceTrueWithFalse at redisdb.py:238 (`get("warn_on_missing_keys", True)`).
    redis_check = check({'host': 'h', 'port': 1, 'db': 2, 'keys': ['k1', 'k2']})
    redis_check.warning = mock.MagicMock()
    conn = make_conn(keyspace=[])
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)

    aggregator.assert_metric(
        'redis.key.length', value=0, count=1, tags=['key:k1', 'redis_db:db2', 'redis_host:h', 'redis_port:1']
    )
    aggregator.assert_metric(
        'redis.key.length', value=0, count=1, tags=['key:k2', 'redis_db:db2', 'redis_host:h', 'redis_port:1']
    )
    assert redis_check.warning.call_count == 3


def test_check_key_lengths_missing_key_with_instance_db(check, aggregator):
    # Kills core/NumberReplacer at redisdb.py:256 (`dbstring[2:]`) and core/AddNot at redisdb.py:259/260/340.
    redis_check = check({'host': 'h', 'port': 1, 'db': 3, 'keys': ['ghost_key']})
    conn = make_conn(keyspace=['db3'])
    conn.type.return_value = 'none'
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    aggregator.assert_metric(
        'redis.key.length', value=0, count=1, tags=['key:ghost_key', 'redis_db:db3', 'redis_host:h', 'redis_port:1']
    )


def test_check_key_lengths_skips_key_on_response_error(check, aggregator):
    # Kills the core/ExceptionReplacer mutant at redisdb.py:286 and core/ReplaceContinueWithBreak at
    # redisdb.py:288 (a `break` would stop processing before `good_key` is reached).
    redis_check = check({'host': 'h', 'port': 1, 'keys': ['pattern*']})
    conn = make_conn(keyspace=['db0'])
    conn.scan_iter.return_value = ['bad_key', 'good_key']
    conn.type.side_effect = [redis.ResponseError('gone'), 'list']
    conn.llen.return_value = 7
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    aggregator.assert_metric(
        'redis.key.length',
        value=7,
        count=1,
        tags=['key:good_key', 'key_type:list', 'redis_db:db0', 'redis_host:h', 'redis_port:1'],
    )


def test_check_key_lengths_all_key_types(check, aggregator):
    # Kills the core/ReplaceComparisonOperator_Eq_* mutants at redisdb.py:290/294/298/302/306/310, the
    # core/NumberReplacer mutants at redisdb.py:308-309/317-318, core/AddNot at redisdb.py:277, and
    # core/ReplaceBinaryOperator_Add_* at redisdb.py:332.
    redis_check = check({'host': 'h', 'port': 1, 'keys': ['listk', 'setk', 'zsetk', 'hashk', 'strk', 'streamk']})
    conn = make_conn(keyspace=['db0'])
    type_map = {
        'listk': 'list',
        'setk': 'set',
        'zsetk': 'zset',
        'hashk': 'hash',
        'strk': 'string',
        'streamk': 'stream',
    }
    conn.type.side_effect = lambda k: type_map[k]
    conn.llen.return_value = 5
    conn.scard.return_value = 6
    conn.zcard.return_value = 7
    conn.hlen.return_value = 8
    conn.xlen.return_value = 9
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)

    base_tags = ['redis_db:db0', 'redis_host:h', 'redis_port:1']
    aggregator.assert_metric('redis.key.length', value=5, tags=['key:listk', 'key_type:list'] + base_tags)
    aggregator.assert_metric('redis.key.length', value=6, tags=['key:setk', 'key_type:set'] + base_tags)
    aggregator.assert_metric('redis.key.length', value=7, tags=['key:zsetk', 'key_type:zset'] + base_tags)
    aggregator.assert_metric('redis.key.length', value=8, tags=['key:hashk', 'key_type:hash'] + base_tags)
    aggregator.assert_metric('redis.key.length', value=1, tags=['key:strk', 'key_type:string'] + base_tags)
    aggregator.assert_metric('redis.key.length', value=9, tags=['key:streamk', 'key_type:stream'] + base_tags)


def test_check_key_lengths_multiple_databases_and_patterns(check, aggregator):
    # Kills the ZeroIterationForLoop mutants at redisdb.py:271 and redisdb.py:276.
    redis_check = check({'host': 'h', 'port': 1, 'keys': ['k1', 'k2']})
    conn = make_conn(keyspace=['db0', 'db1'])
    conn.type.return_value = 'list'
    conn.llen.return_value = 4
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)

    for db in ('db0', 'db1'):
        for key in ('k1', 'k2'):
            aggregator.assert_metric(
                'redis.key.length',
                value=4,
                count=1,
                tags=[
                    'key:{}'.format(key),
                    'key_type:list',
                    'redis_db:{}'.format(db),
                    'redis_host:h',
                    'redis_port:1',
                ],
            )
    aggregator.assert_metric('redis.key.length', count=4)


def test_check_replication_computes_slave_delay_and_tags(check, aggregator):
    # Kills core/ReplaceAndWithOr at redisdb.py:350, core/NumberReplacer at redisdb.py:351,
    # core/ReplaceBinaryOperator_Sub_* at redisdb.py:354, ZeroIterationForLoop at redisdb.py:357,
    # and core/ReplaceBinaryOperator_Mod_Add mutant at redisdb.py:360 (`'slave_id:%s' % ...`).
    redis_check = check({'host': 'h', 'port': 1, 'tags': ['foo:bar']})
    conn = make_conn(
        info={
            'slave0': {'offset': 80, 'ip': '10.0.0.5', 'port': '6380'},
            'slaveBAD': 'not-a-dict',
            'master_repl_offset': 100,
            'master_link_status': 'up',
        }
    )
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)

    base_tags = ['redis_host:h', 'redis_port:1', 'foo:bar']
    aggregator.assert_metric(
        'redis.replication.delay',
        value=20,
        count=1,
        tags=base_tags + ['slave_ip:10.0.0.5', 'slave_port:6380', 'slave_id:0'],
    )
    aggregator.assert_service_check('redis.replication.master_link_status', status=redis_check.OK, tags=base_tags)
    aggregator.assert_metric('redis.replication.master_link_down_since_seconds', value=0, tags=base_tags)


def test_check_replication_missing_slave_offset_defaults_to_zero(check, aggregator):
    # Kills the core/NumberReplacer mutant at redisdb.py:351 (`info[key].get('offset', 0)`) and
    # core/AddNot at redisdb.py:358 (`if slave_tag in info[key]:`).
    redis_check = check({'host': 'h', 'port': 1})
    conn = make_conn(info={'slave1': {}, 'master_repl_offset': 100})
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    aggregator.assert_metric(
        'redis.replication.delay', value=100, count=1, tags=['redis_host:h', 'redis_port:1', 'slave_id:1']
    )


def test_check_replication_missing_master_offset_defaults_to_zero(check, aggregator):
    # Kills the core/NumberReplacer mutant at redisdb.py:352 (`info.get('master_repl_offset', 0)`).
    redis_check = check({'host': 'h', 'port': 1})
    conn = make_conn(info={'slave0': {'offset': 0}})
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    aggregator.assert_metric(
        'redis.replication.delay', value=0, count=1, tags=['redis_host:h', 'redis_port:1', 'slave_id:0']
    )


def test_check_replication_negative_delay_is_not_reported(check, aggregator):
    # Kills core/AddNot and several core/ReplaceComparisonOperator_GtE_* mutants at redisdb.py:353
    # (`if master_offset - slave_offset >= 0:`).
    redis_check = check({'host': 'h', 'port': 1})
    conn = make_conn(info={'slave0': {'offset': 40}, 'master_repl_offset': 39})
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    aggregator.assert_metric('redis.replication.delay', count=0)


def test_check_replication_master_link_down(check, aggregator):
    # Kills core/AddNot and core/ReplaceComparisonOperator_Eq_* mutants at redisdb.py:364 and the
    # core/NumberReplacer mutant at redisdb.py:366 (`down_seconds = 0`).
    redis_check = check({'host': 'h', 'port': 1, 'tags': ['foo:bar']})
    conn = make_conn(info={'master_link_status': 'down', 'master_link_down_since_seconds': 30})
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)

    base_tags = ['redis_host:h', 'redis_port:1', 'foo:bar']
    aggregator.assert_service_check('redis.replication.master_link_status', status=redis_check.CRITICAL, tags=base_tags)
    aggregator.assert_metric('redis.replication.master_link_down_since_seconds', value=30, tags=base_tags)


def test_check_slowlog_parses_raw_response(check):
    # Kills core/NumberReplacer at redisdb.py:412-414, core/AddNot at redisdb.py:409 and redisdb.py:419
    # (the `isinstance(item[3], list)` fallback to `item[4]`), inside `upstream_parse_slowlog_get`.
    redis_check = check({'host': 'h', 'port': 1})
    conn = make_conn()
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)

    callback = conn.set_response_callback.call_args[0][1]

    parsed = callback([(42, 1000, 500, [b'SET', b'foo', b'bar'])])
    assert parsed == [{'id': 42, 'start_time': 1000, 'duration': 500, 'command': b'SET foo bar'}]

    parsed_enterprise = callback([(44, 1002, 700, 3, [b'LPUSH', b'k', b'v'])])
    assert parsed_enterprise == [{'id': 44, 'start_time': 1002, 'duration': 700, 'command': b'LPUSH k v'}]

    parsed_decoded = callback([(45, 1003, 800, ['GET', 'foo'])], decode_responses=True)
    assert parsed_decoded == [{'id': 45, 'start_time': 1003, 'duration': 800, 'command': 'GET foo'}]


def test_check_slowlog_caps_configured_max_entries_at_default(check):
    # Kills core/ReplaceComparisonOperator_Gt_* and core/AddNot mutants at redisdb.py:429.
    redis_check = check({'host': 'h', 'port': 1})
    conn = make_conn(slowlog_max_len='999')
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    conn.slowlog_get.assert_called_once_with(DEFAULT_MAX_SLOW_ENTRIES)


def test_check_slowlog_keeps_configured_value_below_default(check):
    # Kills the core/ReplaceComparisonOperator_Gt_NotEq mutant at redisdb.py:429.
    redis_check = check({'host': 'h', 'port': 1})
    conn = make_conn(slowlog_max_len='10')
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    conn.slowlog_get.assert_called_once_with(10)


def test_check_slowlog_filters_old_entries_and_tracks_timestamp(check, aggregator):
    # Kills core/ReplaceComparisonOperator_Gt_* at redisdb.py:452/461/466, ZeroIterationForLoop at
    # redisdb.py:460, core/NumberReplacer at redisdb.py:467, and core/AddNot at redisdb.py:472.
    redis_check = check({'host': 'h', 'port': 1})
    redis_check.last_timestamp_seen = 100
    conn = make_conn(
        slowlog_entries=[
            {'id': 1, 'start_time': 50, 'duration': 10, 'command': 'OLD ignored'},
            {'id': 2, 'start_time': 150, 'duration': 20, 'command': 'GET key'},
            {'id': 3, 'start_time': 200, 'duration': 30, 'command': 'SET key val'},
            {'id': 4, 'start_time': 250, 'duration': 40, 'command': ''},
        ]
    )
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)

    base_tags = ['redis_host:h', 'redis_port:1']
    aggregator.assert_metric('redis.slowlog.micros', count=3)
    aggregator.assert_metric('redis.slowlog.micros', value=20, tags=base_tags + ['command:GET'])
    aggregator.assert_metric('redis.slowlog.micros', value=30, tags=base_tags + ['command:SET'])
    aggregator.assert_metric('redis.slowlog.micros', value=40, tags=base_tags)
    assert redis_check.last_timestamp_seen == 250


def test_check_slowlog_no_new_entries_keeps_previous_timestamp(check, aggregator):
    # Kills the core/NumberReplacer mutant at redisdb.py:454 (`max_ts = 0`) and core/AddNot at redisdb.py:472.
    redis_check = check({'host': 'h', 'port': 1})
    redis_check.last_timestamp_seen = 500
    conn = make_conn(slowlog_entries=[{'id': 1, 'start_time': 100, 'duration': 5, 'command': 'GET x'}])
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    aggregator.assert_metric('redis.slowlog.micros', count=0)
    assert redis_check.last_timestamp_seen == 500


def test_check_command_stats_swallows_info_errors(check, aggregator):
    # Kills the core/ExceptionReplacer mutant at redisdb.py:479 (`except Exception:`).
    redis_check = check({'host': 'h', 'port': 1, 'command_stats': True})
    conn = make_conn()

    def info_side_effect(*args, **kwargs):
        if args and args[0] == 'commandstats':
            raise RuntimeError('boom')
        return {}

    conn.info.side_effect = info_side_effect
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    aggregator.assert_metric('redis.command.calls', count=0)


def test_check_collect_metadata_sets_version_when_present(check):
    # Kills the core/AddNot mutant at redisdb.py:499 (`if info and 'redis_version' in info:`).
    redis_check = check({'host': 'h', 'port': 1})
    redis_check.set_metadata = mock.MagicMock()
    conn = make_conn(info={'redis_version': '7.2.0'})
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    redis_check.set_metadata.assert_called_once_with('version', '7.2.0')


def test_check_collect_metadata_skips_when_version_missing(check):
    # Kills the core/ReplaceAndWithOr mutant at redisdb.py:499 (`if info and 'redis_version' in info:`).
    redis_check = check({'host': 'h', 'port': 1})
    redis_check.set_metadata = mock.MagicMock()
    conn = make_conn(info={'other_key': 'value'})
    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check.check(None)
    redis_check.set_metadata.assert_not_called()


def test_check_reports_info_and_ping_latency(check, aggregator):
    # Kills every core/ReplaceBinaryOperator_Sub_*/Mul_* and core/NumberReplacer mutant at redisdb.py:507,
    # inside the module-level `_call_and_time` helper used to time both the INFO and PING calls.
    redis_check = check({'host': 'h', 'port': 1})
    conn = make_conn()
    with (
        mock.patch.object(redis_check, '_get_conn', return_value=conn),
        mock.patch('datadog_checks.redisdb.redisdb.time.perf_counter', side_effect=[0.5, 2.123456, 10.0, 10.001]),
    ):
        redis_check.check(None)

    base_tags = ['redis_host:h', 'redis_port:1']
    aggregator.assert_metric('redis.info.latency_ms', value=1623.46, tags=base_tags)
    aggregator.assert_metric('redis.ping.latency_ms', value=1.0, tags=base_tags)
