# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import re
import time
from collections import Counter, defaultdict
from copy import deepcopy

import redis

from datadog_checks.base import AgentCheck, ConfigurationError, ensure_unicode, is_affirmative
from datadog_checks.base.utils.common import round_value

from .constants import (
    CONFIG_GAUGE_KEYS,
    DEFAULT_CLIENT_NAME,
    DEFAULT_MAX_SLOW_ENTRIES,
    GAUGE_KEYS,
    LINK_DOWN_KEY,
    MAX_SLOW_ENTRIES_KEY,
    RATE_KEYS,
    REPL_KEY,
)


class Redis(AgentCheck):
    db_key_pattern = re.compile(r'^db\d+$')
    slave_key_pattern = re.compile(r'^slave\d+')
    subkeys = ['keys', 'expires']

    SOURCE_TYPE_NAME = 'redis'

    def __init__(self, name, init_config, instances):
        super(Redis, self).__init__(name, init_config, instances)
        self.connections = {}
        self.last_timestamp_seen = 0
        custom_tags = self.instance.get('tags', [])
        self.tags = self._get_tags(custom_tags)
        self.collect_client_metrics = is_affirmative(self.instance.get('collect_client_metrics', False))
        if ("host" not in self.instance or "port" not in self.instance) and "unix_socket_path" not in self.instance:
            raise ConfigurationError("You must specify a host/port couple or a unix_socket_path")

    def get_library_versions(self):
        return {"redis": redis.__version__}

    def _parse_dict_string(self, string, key, default):
        """Take from a more recent redis.py, parse_info"""
        try:
            for item in string.split(','):
                k, v = item.rsplit('=', 1)
                if k == key:
                    try:
                        return int(v)
                    except ValueError:
                        return v
            return default
        except Exception:
            self.log.exception("Cannot parse dictionary string: %s", string)
            return default

    @staticmethod
    def _generate_instance_key(instance_config):
        if 'unix_socket_path' in instance_config:
            return instance_config.get('unix_socket_path'), instance_config.get('db')
        else:
            return instance_config.get('host'), instance_config.get('port'), instance_config.get('db')

    def _get_conn(self, instance_config):
        no_cache = is_affirmative(instance_config.get('disable_connection_cache', False))
        key = self._generate_instance_key(instance_config)

        if no_cache or key not in self.connections:
            try:
                # Only send useful parameters to the redis client constructor
                list_params = [
                    'host',
                    'port',
                    'db',
                    'username',
                    'password',
                    'socket_timeout',
                    'unix_socket_path',
                    'ssl',
                    'ssl_certfile',
                    'ssl_keyfile',
                    'ssl_ca_certs',
                    'ssl_cert_reqs',
                ]

                # Set a default timeout (in seconds) if no timeout is specified in the instance config
                instance_config['socket_timeout'] = instance_config.get('socket_timeout', 5)
                connection_params = {k: instance_config[k] for k in list_params if k in instance_config}
                # If caching is disabled, we overwrite the dictionary value so the old connection
                # will be closed as soon as the corresponding Python object gets garbage collected
                self.connections[key] = redis.Redis(**connection_params)

            except TypeError:
                msg = "You need a redis library that supports authenticated connections. Try `pip install redis`."
                raise Exception(msg)

        return self.connections[key]

    def _get_tags(self, custom_tags):
        if 'unix_socket_path' in self.instance:
            tags_to_add = {"redis_host:%s" % self.instance.get("unix_socket_path"), "redis_port:unix_socket"}
        else:
            tags_to_add = {"redis_host:%s" % self.instance.get('host'), "redis_port:%s" % self.instance.get('port')}

        tags = sorted(tags_to_add.union(custom_tags))
        return tags

    def _check_db(self):
        tags = list(self.tags)
        conn = self._get_conn(self.instance)

        # Ping the database for info, and track the latency.
        # Process the service check: the check passes if we can connect to Redis
        try:
            # By running a ping first, we get a recent connection in an attempt to
            # reduce the chance of connection time affecting our latency measurements
            conn.ping()

            try:
                info, info_latency_ms = _call_and_time(
                    conn.info, section='all'
                )  # not available on older versions of Redis
            except redis.ResponseError as e:
                self.log.debug('`INFO all` command failed, falling back to `INFO`: %s', e)
                info, info_latency_ms = _call_and_time(conn.info)
            _, ping_latency_ms = _call_and_time(conn.ping)

            self._collect_metadata(info)
        except ValueError as e:
            self.service_check('redis.can_connect', AgentCheck.CRITICAL, message=str(e), tags=self.tags)
            raise
        except Exception as e:
            self.service_check('redis.can_connect', AgentCheck.CRITICAL, message=str(e), tags=self.tags)
            raise
        else:
            self.service_check('redis.can_connect', AgentCheck.OK, tags=tags)

        if info.get("role"):
            tags.append("redis_role:{}".format(info["role"]))
        else:
            self.log.debug("Redis role was not found")

        self.gauge('redis.info.latency_ms', info_latency_ms, tags=tags)
        self.gauge('redis.ping.latency_ms', ping_latency_ms, tags=tags)

        try:
            config = conn.config_get("maxclients")
        except redis.ResponseError:
            # config_get is disabled on some environments
            self.log.debug("Unable to collect max clients: CONFIG GET disabled in managed Redis instances.")
            config = {}

        # Save the database statistics.
        for key in info.keys():
            if self.db_key_pattern.match(key):
                db_tags = tags + ["redis_db:" + key]
                # allows tracking percentage of expired keys as DD does not
                # currently allow arithmetic on metric for monitoring
                expires_keys = info[key]["expires"]
                total_keys = info[key]["keys"]
                persist_keys = total_keys - expires_keys
                self.gauge("redis.persist", persist_keys, tags=db_tags)
                self.gauge("redis.persist.percent", 100 * persist_keys / total_keys, tags=db_tags)
                self.gauge("redis.expires.percent", 100 * expires_keys / total_keys, tags=db_tags)

                for subkey in self.subkeys:
                    # Old redis module on ubuntu 10.04 (python-redis 0.6.1) does not
                    # returns a dict for those key but a string: keys=3,expires=0
                    # Try to parse it (see lighthouse #46)
                    try:
                        val = info[key].get(subkey, -1)
                    except AttributeError:
                        val = self._parse_dict_string(info[key], subkey, -1)
                    metric = 'redis.{}'.format(subkey)
                    self.gauge(metric, val, tags=db_tags)

        # Save a subset of db-wide statistics
        self._check_info_fields(info, tags)
        for config_key, value in config.items():
            metric_name = CONFIG_GAUGE_KEYS.get(config_key)
            if metric_name is not None:
                self.gauge(metric_name, value, tags=tags)

        if self.collect_client_metrics:
            try:
                # Save client connections statistics
                clients = conn.client_list()
                clients_by_name = Counter(client["name"] or DEFAULT_CLIENT_NAME for client in clients)
                for name, count in clients_by_name.items():
                    self.gauge("redis.net.connections", count, tags=tags + ['source:' + name])
            except redis.ResponseError:
                # client_list is disabled on some environments
                self.log.debug("Unable to collect client metrics: CLIENT disabled in some managed Redis.")

        # Check some key lengths if asked
        self._check_key_lengths(conn, list(tags))

        # Check replication
        self._check_replication(info, tags)
        if self.instance.get("command_stats", False):
            self._check_command_stats(conn, tags)

    def _check_info_fields(self, info, tags):
        for info_name in info:
            if info_name in GAUGE_KEYS:
                self.gauge(GAUGE_KEYS[info_name], info[info_name], tags=tags)
            elif info_name in RATE_KEYS:
                self.rate(RATE_KEYS[info_name], info[info_name], tags=tags)
            else:
                self.log.debug('Not collecting INFO field %s', info_name)

    def _check_key_lengths(self, conn, tags):
        """
        Compute the length of the configured keys across all the databases
        """
        key_list = self.instance.get('keys')

        if key_list is None:
            return

        instance_db = self.instance.get('db')

        if not isinstance(key_list, list) or not key_list:
            self.warning("keys in redis configuration is either not a list or empty")
            return

        warn_on_missing_keys = is_affirmative(self.instance.get("warn_on_missing_keys", True))

        # get all the available databases
        databases = list(conn.info('keyspace'))
        if not databases:
            self.warning("Redis database is empty")
            for key in key_list:
                key_tags = ['key:{}'.format(key)]
                if instance_db:
                    key_tags.append('redis_db:db{}'.format(instance_db))
                key_tags.extend(tags)
                self.gauge('redis.key.length', 0, tags=key_tags)
                if warn_on_missing_keys:
                    self.warning("%s key not found in redis", key)
            return

        # convert to integer the output of `keyspace`, from `db0` to `0`
        # and store items in a set
        databases = [int(dbstring[2:]) for dbstring in databases]

        # user might have configured the instance to target one specific db
        if instance_db:
            if instance_db not in databases:
                self.warning("Cannot find database %s", instance_db)
                return
            databases = [instance_db]

        # maps a key to the total length across databases
        lengths_overall = defaultdict(int)

        # don't overwrite the configured instance, use a copy
        tmp_instance = deepcopy(self.instance)

        for db in databases:
            lengths = defaultdict(lambda: defaultdict(int))
            tmp_instance['db'] = db
            db_conn = self._get_conn(tmp_instance)

            for key_pattern in key_list:
                if re.search(r"(?<!\\)[*?[]", key_pattern):
                    keys = db_conn.scan_iter(match=key_pattern)
                else:
                    keys = [key_pattern]

                for key in keys:
                    text_key = ensure_unicode(key)
                    try:
                        key_type = ensure_unicode(db_conn.type(key))
                    except redis.ResponseError:
                        self.log.info("key %s on remote server; skipping", text_key)
                        continue

                    if key_type == 'list':
                        keylen = db_conn.llen(key)
                        lengths[text_key]["length"] += keylen
                        lengths_overall[text_key] += keylen
                    elif key_type == 'set':
                        keylen = db_conn.scard(key)
                        lengths[text_key]["length"] += keylen
                        lengths_overall[text_key] += keylen
                    elif key_type == 'zset':
                        keylen = db_conn.zcard(key)
                        lengths[text_key]["length"] += keylen
                        lengths_overall[text_key] += keylen
                    elif key_type == 'hash':
                        keylen = db_conn.hlen(key)
                        lengths[text_key]["length"] += keylen
                        lengths_overall[text_key] += keylen
                    elif key_type == 'string':
                        # Send 1 if the key exists as a string
                        lengths[text_key]["length"] += 1
                        lengths_overall[text_key] += 1
                    elif key_type == 'stream':
                        keylen = db_conn.xlen(key)
                        lengths[text_key]["length"] += keylen
                        lengths_overall[text_key] += keylen
                    else:
                        # If the type is unknown, it might be because the key doesn't exist,
                        # which can be because the list is empty. So always send 0 in that case.
                        lengths[text_key]["length"] += 0
                        lengths_overall[text_key] += 0

                    # Tagging with key_type since the same key can exist with a
                    # different key_type in another db
                    lengths[text_key]["key_type"] = key_type

            # Send the metrics for each db in the redis instance.
            for key, total in lengths.items():
                # Only send non-zeros if tagged per db.
                if total["length"] > 0:
                    self.gauge(
                        'redis.key.length',
                        total["length"],
                        tags=tags
                        + ['key:{}'.format(key), 'key_type:{}'.format(total["key_type"]), 'redis_db:db{}'.format(db)],
                    )

        # Warn if a key is missing from the entire redis instance.
        # Send 0 if the key is missing/empty from the entire redis instance.
        for key, total in lengths_overall.items():
            if total == 0:
                key_tags = ['key:{}'.format(key)]
                if instance_db:
                    key_tags.append('redis_db:db{}'.format(instance_db))
                key_tags.extend(tags)
                self.gauge('redis.key.length', 0, tags=key_tags)
                if warn_on_missing_keys:
                    self.warning("%s key not found in redis", key)

    def _check_replication(self, info, tags):
        # Save the replication delay for each slave
        for key in info:
            if self.slave_key_pattern.match(key) and isinstance(info[key], dict):
                slave_offset = info[key].get('offset', 0)
                master_offset = info.get('master_repl_offset', 0)
                if master_offset - slave_offset >= 0:
                    delay = master_offset - slave_offset
                    # Add id, ip, and port tags for the slave
                    slave_tags = tags[:]
                    for slave_tag in ('ip', 'port'):
                        if slave_tag in info[key]:
                            slave_tags.append('slave_{}:{}'.format(slave_tag, info[key][slave_tag]))
                    slave_tags.append('slave_id:%s' % key.lstrip('slave'))
                    self.gauge('redis.replication.delay', delay, tags=slave_tags)

        if REPL_KEY in info:
            if info[REPL_KEY] == 'up':
                status = AgentCheck.OK
                down_seconds = 0
            else:
                status = AgentCheck.CRITICAL
                down_seconds = info[LINK_DOWN_KEY]

            self.service_check('redis.replication.master_link_status', status, tags=tags)
            self.gauge('redis.replication.master_link_down_since_seconds', down_seconds, tags=tags)

    def _check_slowlog(self):
        """Retrieve length and entries from Redis' SLOWLOG

        This will parse through all entries of the SLOWLOG and select ones
        within the time range between the last seen entries and now

        """
        conn = self._get_conn(self.instance)

        # Use fixed version of parse_slowlog_get callback for the
        # 'SLOWLOG GET' command; taken from upstream/master since it
        # will not be released in redis==3.5.3
        # - https://github.com/andymccurdy/redis-py/issues/1428#issuecomment-749692873
        # - upstream/master: https://github.com/andymccurdy/redis-py/commit/bc5854217b4e94eb7a33e3da5738858a17135ca5
        def upstream_parse_slowlog_get(response, **options):
            space = ' ' if options.get('decode_responses', False) else b' '
            return [
                {
                    'id': item[0],
                    'start_time': int(item[1]),
                    'duration': int(item[2]),
                    'command':
                    # Redis Enterprise injects another entry at index [3], which has
                    # the complexity info (i.e. the value N in case the command has
                    # an O(N) complexity) instead of the command.
                    space.join(item[3]) if isinstance(item[3], list) else space.join(item[4]),
                }
                for item in response
            ]

        conn.set_response_callback("SLOWLOG GET", upstream_parse_slowlog_get)

        if not self.instance.get(MAX_SLOW_ENTRIES_KEY):
            try:
                max_slow_entries = int(conn.config_get(MAX_SLOW_ENTRIES_KEY)[MAX_SLOW_ENTRIES_KEY])
                if max_slow_entries > DEFAULT_MAX_SLOW_ENTRIES:
                    self.log.debug(
                        "Redis {0} is higher than {1}. Defaulting to {1}. "  # noqa: G001
                        "If you need a higher value, please set {0} in your check config".format(
                            MAX_SLOW_ENTRIES_KEY, DEFAULT_MAX_SLOW_ENTRIES
                        )
                    )
                    max_slow_entries = DEFAULT_MAX_SLOW_ENTRIES
            # No config on AWS Elasticache
            except redis.ResponseError:
                self.log.debug("Unable to collect length of slow log: CONFIG GET disabled in some managed Redis.")
                max_slow_entries = DEFAULT_MAX_SLOW_ENTRIES
        else:
            max_slow_entries = int(self.instance.get(MAX_SLOW_ENTRIES_KEY))

        # Get all slowlog entries
        try:
            slowlogs = conn.slowlog_get(max_slow_entries)
        except redis.ResponseError:
            self.log.debug("Unable to collect slow log: SLOWLOG GET disabled in some managed Redis.")
            return

        # Find slowlog entries between last timestamp and now using start_time
        slowlogs = [s for s in slowlogs if s['start_time'] > self.last_timestamp_seen]

        max_ts = 0
        # Slowlog entry looks like:
        #  {'command': 'LPOP somekey',
        #   'duration': 11238,
        #   'id': 496L,
        #   'start_time': 1422529869}
        for slowlog in slowlogs:
            if slowlog['start_time'] > max_ts:
                max_ts = slowlog['start_time']

            slowlog_tags = list(self.tags)
            command = slowlog['command'].split()
            if len(command) > 0:
                slowlog_tags.append('command:{}'.format(ensure_unicode(command[0])))

            value = slowlog['duration']
            self.histogram('redis.slowlog.micros', value, tags=slowlog_tags)

        if max_ts != 0:
            self.last_timestamp_seen = max_ts

    def _check_command_stats(self, conn, tags):
        """Get command-specific statistics from redis' INFO COMMANDSTATS command"""
        try:
            command_stats = conn.info("commandstats")
        except Exception:
            self.warning('Could not retrieve command stats from Redis. INFO COMMANDSTATS only works with Redis >= 2.6.')
            return

        for key, stats in command_stats.items():
            command = key.split('_', 1)[1]
            command_tags = tags + ['command:{}'.format(command)]

            # When `host:` is passed as a command, `calls` ends up having a leading `:`
            # see https://github.com/DataDog/integrations-core/issues/839
            calls = stats.get('calls') if command != 'host' else stats.get(':calls')

            self.gauge('redis.command.calls', calls, tags=command_tags)
            self.gauge('redis.command.usec_per_call', stats['usec_per_call'], tags=command_tags)

    def check(self, _):
        self._check_db()
        self._check_slowlog()

    def _collect_metadata(self, info):
        if info and 'redis_version' in info:
            self.set_metadata('version', info['redis_version'])


def _call_and_time(func, *args, **kwargs):
    start_time = time.perf_counter()
    rv = func(*args, **kwargs)
    end_time = time.perf_counter()
    return rv, round_value((end_time - start_time) * 1000, 2)
