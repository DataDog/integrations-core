# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re
import time
from collections import defaultdict
from copy import deepcopy

import redis
from six import iteritems

from datadog_checks.checks import AgentCheck
from datadog_checks.config import is_affirmative

DEFAULT_MAX_SLOW_ENTRIES = 128
MAX_SLOW_ENTRIES_KEY = "slowlog-max-len"

REPL_KEY = 'master_link_status'
LINK_DOWN_KEY = 'master_link_down_since_seconds'


class Redis(AgentCheck):
    db_key_pattern = re.compile(r'^db\d+')
    slave_key_pattern = re.compile(r'^slave\d+')
    subkeys = ['keys', 'expires']

    SOURCE_TYPE_NAME = 'redis'

    GAUGE_KEYS = {
        # Append-only metrics
        'aof_last_rewrite_time_sec':    'redis.aof.last_rewrite_time',
        'aof_rewrite_in_progress':      'redis.aof.rewrite',
        'aof_current_size':             'redis.aof.size',
        'aof_buffer_length':            'redis.aof.buffer_length',

        # Network
        'connected_clients':            'redis.net.clients',
        'connected_slaves':             'redis.net.slaves',
        'rejected_connections':         'redis.net.rejected',

        # clients
        'blocked_clients':              'redis.clients.blocked',
        'client_biggest_input_buf':     'redis.clients.biggest_input_buf',
        'client_longest_output_list':   'redis.clients.longest_output_list',

        # Keys
        'evicted_keys':                 'redis.keys.evicted',
        'expired_keys':                 'redis.keys.expired',

        # stats
        'latest_fork_usec':             'redis.perf.latest_fork_usec',
        'bytes_received_per_sec':       'redis.bytes_received_per_sec',
        'bytes_sent_per_sec':           'redis.bytes_sent_per_sec',
        # Note: 'bytes_received_per_sec' and 'bytes_sent_per_sec' are only
        # available on Azure Redis

        # pubsub
        'pubsub_channels':              'redis.pubsub.channels',
        'pubsub_patterns':              'redis.pubsub.patterns',

        # rdb
        'rdb_bgsave_in_progress':       'redis.rdb.bgsave',
        'rdb_changes_since_last_save':  'redis.rdb.changes_since_last',
        'rdb_last_bgsave_time_sec':     'redis.rdb.last_bgsave_time',

        # memory
        'mem_fragmentation_ratio':      'redis.mem.fragmentation_ratio',
        'used_memory':                  'redis.mem.used',
        'used_memory_lua':              'redis.mem.lua',
        'used_memory_peak':             'redis.mem.peak',
        'used_memory_rss':              'redis.mem.rss',
        'maxmemory':                    'redis.mem.maxmemory',

        # replication
        'master_last_io_seconds_ago':   'redis.replication.last_io_seconds_ago',
        'master_sync_in_progress':      'redis.replication.sync',
        'master_sync_left_bytes':       'redis.replication.sync_left_bytes',
        'repl_backlog_histlen':         'redis.replication.backlog_histlen',
        'master_repl_offset':           'redis.replication.master_repl_offset',
        'slave_repl_offset':            'redis.replication.slave_repl_offset',
    }

    RATE_KEYS = {
        # cpu
        'used_cpu_sys':                 'redis.cpu.sys',
        'used_cpu_sys_children':        'redis.cpu.sys_children',
        'used_cpu_user':                'redis.cpu.user',
        'used_cpu_user_children':       'redis.cpu.user_children',

        # stats
        'keyspace_hits':                'redis.stats.keyspace_hits',
        'keyspace_misses':              'redis.stats.keyspace_misses',
    }

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.connections = {}
        self.last_timestamp_seen = defaultdict(int)

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
            self.log.exception("Cannot parse dictionary string: %s" % string)
            return default

    def _generate_instance_key(self, instance):
        if 'unix_socket_path' in instance:
            return (instance.get('unix_socket_path'), instance.get('db'))
        else:
            return (instance.get('host'), instance.get('port'), instance.get('db'))

    def _get_conn(self, instance):
        no_cache = is_affirmative(instance.get('disable_connection_cache', False))
        key = self._generate_instance_key(instance)

        if no_cache or key not in self.connections:
            try:
                # Only send useful parameters to the redis client constructor
                list_params = [
                    'host', 'port', 'db', 'password', 'socket_timeout',
                    'connection_pool', 'charset', 'errors', 'unix_socket_path', 'ssl',
                    'ssl_certfile', 'ssl_keyfile', 'ssl_ca_certs', 'ssl_cert_reqs'
                ]

                # Set a default timeout (in seconds) if no timeout is specified in the instance config
                instance['socket_timeout'] = instance.get('socket_timeout', 5)
                connection_params = dict((k, instance[k]) for k in list_params if k in instance)
                # If caching is disabled, we overwrite the dictionary value so the old connection
                # will be closed as soon as the corresponding Python object gets garbage collected
                self.connections[key] = redis.Redis(**connection_params)

            except TypeError:
                msg = "You need a redis library that supports authenticated connections. Try sudo easy_install redis."
                raise Exception(msg)

        return self.connections[key]

    def _get_tags(self, custom_tags, instance):
        tags = set(custom_tags or [])

        if 'unix_socket_path' in instance:
            tags_to_add = [
                "redis_host:%s" % instance.get("unix_socket_path"),
                "redis_port:unix_socket",
            ]
        else:
            tags_to_add = [
                "redis_host:%s" % instance.get('host'),
                "redis_port:%s" % instance.get('port')
            ]

        tags = sorted(tags.union(tags_to_add))

        return tags

    def _check_db(self, instance, custom_tags=None):
        conn = self._get_conn(instance)
        tags = self._get_tags(custom_tags, instance)

        # Ping the database for info, and track the latency.
        # Process the service check: the check passes if we can connect to Redis
        start = time.time()
        info = None
        try:
            info = conn.info()
            tags = sorted(tags + ["redis_role:%s" % info["role"]])
            status = AgentCheck.OK
            self.service_check('redis.can_connect', status, tags=tags)
            self._collect_metadata(info)
        except ValueError:
            status = AgentCheck.CRITICAL
            self.service_check('redis.can_connect', status, tags=tags)
            raise
        except Exception:
            status = AgentCheck.CRITICAL
            self.service_check('redis.can_connect', status, tags=tags)
            raise

        latency_ms = round((time.time() - start) * 1000, 2)
        self.gauge('redis.info.latency_ms', latency_ms, tags=tags)

        # Save the database statistics.
        for key in info.keys():
            if self.db_key_pattern.match(key):
                db_tags = list(tags) + ["redis_db:" + key]
                # allows tracking percentage of expired keys as DD does not
                # currently allow arithmetic on metric for monitoring
                expires_keys = info[key]["expires"]
                total_keys = info[key]["keys"]
                persist_keys = total_keys - expires_keys
                self.gauge("redis.persist", persist_keys, tags=db_tags)
                self.gauge("redis.persist.percent", 100.0 * persist_keys / total_keys, tags=db_tags)
                self.gauge("redis.expires.percent", 100.0 * expires_keys / total_keys, tags=db_tags)

                for subkey in self.subkeys:
                    # Old redis module on ubuntu 10.04 (python-redis 0.6.1) does not
                    # returns a dict for those key but a string: keys=3,expires=0
                    # Try to parse it (see lighthouse #46)
                    val = -1
                    try:
                        val = info[key].get(subkey, -1)
                    except AttributeError:
                        val = self._parse_dict_string(info[key], subkey, -1)
                    metric = '.'.join(['redis', subkey])
                    self.gauge(metric, val, tags=db_tags)

        # Save a subset of db-wide statistics
        for info_name, value in info.iteritems():
            if info_name in self.GAUGE_KEYS:
                self.gauge(self.GAUGE_KEYS[info_name], info[info_name], tags=tags)
            elif info_name in self.RATE_KEYS:
                self.rate(self.RATE_KEYS[info_name], info[info_name], tags=tags)

        # Save the number of commands.
        self.rate('redis.net.commands', info['total_commands_processed'],
                  tags=tags)
        if 'instantaneous_ops_per_sec' in info:
            self.gauge('redis.net.instantaneous_ops_per_sec', info['instantaneous_ops_per_sec'],
                       tags=tags)

        # Check some key lengths if asked
        self._check_key_lengths(conn, instance, list(tags))

        # Check replication
        self._check_replication(info, tags)
        if instance.get("command_stats", False):
            self._check_command_stats(conn, tags)

    def _check_key_lengths(self, conn, instance, tags):
        """
        Compute the length of the configured keys across all the databases
        """
        key_list = instance.get('keys')

        if key_list is None:
            return

        if not isinstance(key_list, list) or len(key_list) == 0:
            self.warning("keys in redis configuration is either not a list or empty")
            return

        # get all the available databases
        databases = conn.info('keyspace').keys()
        if not databases:
            self.warning("Redis database is empty")
            return

        # convert to integer the output of `keyspace`, from `db0` to `0`
        # and store items in a set
        databases = [int(dbstring[2:]) for dbstring in databases]

        # user might have configured the instance to target one specific db
        if 'db' in instance:
            db = instance['db']
            if db not in databases:
                self.warning("Cannot find database {}".format(instance['db']))
                return
            databases = [db, ]

        # maps a key to the total length across databases
        lengths = defaultdict(int)

        # don't overwrite the configured instance, use a copy
        tmp_instance = deepcopy(instance)

        for db in databases:
            tmp_instance['db'] = db
            db_conn = self._get_conn(tmp_instance)

            for key_pattern in key_list:
                if re.search(r"(?<!\\)[*?[]", key_pattern):
                    keys = db_conn.scan_iter(match=key_pattern)
                else:
                    keys = [key_pattern, ]

                for key in keys:
                    try:
                        key_type = db_conn.type(key)
                    except redis.ResponseError:
                        self.log.info("key {} on remote server; skipping".format(key))
                        continue

                    if key_type == 'list':
                        lengths[key] += db_conn.llen(key)
                    elif key_type == 'set':
                        lengths[key] += db_conn.scard(key)
                    elif key_type == 'zset':
                        lengths[key] += db_conn.zcard(key)
                    elif key_type == 'hash':
                        lengths[key] += db_conn.hlen(key)
                    else:
                        # If the type is unknown, it might be because the key doesn't exist,
                        # which can be because the list is empty. So always send 0 in that case.
                        lengths[key] += 0

        # send the metrics
        for key, total in iteritems(lengths):
            self.gauge('redis.key.length', total, tags=tags + ['key:' + key])
            if total == 0 and instance.get("warn_on_missing_keys", True):
                self.warning("{0} key not found in redis".format(key))

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
                            slave_tags.append('slave_{0}:{1}'.format(slave_tag, info[key][slave_tag]))
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

    def _check_slowlog(self, instance, custom_tags):
        """Retrieve length and entries from Redis' SLOWLOG

        This will parse through all entries of the SLOWLOG and select ones
        within the time range between the last seen entries and now

        """
        conn = self._get_conn(instance)

        tags = self._get_tags(custom_tags, instance)

        if not instance.get(MAX_SLOW_ENTRIES_KEY):
            try:
                max_slow_entries = int(conn.config_get(MAX_SLOW_ENTRIES_KEY)[MAX_SLOW_ENTRIES_KEY])
                if max_slow_entries > DEFAULT_MAX_SLOW_ENTRIES:
                    self.warning("Redis {0} is higher than {1}. Defaulting to {1}."
                                 "If you need a higher value, please set {0} in your check config"
                                 .format(MAX_SLOW_ENTRIES_KEY, DEFAULT_MAX_SLOW_ENTRIES))
                    max_slow_entries = DEFAULT_MAX_SLOW_ENTRIES
            # No config on AWS Elasticache
            except redis.ResponseError:
                max_slow_entries = DEFAULT_MAX_SLOW_ENTRIES
        else:
            max_slow_entries = int(instance.get(MAX_SLOW_ENTRIES_KEY))

        # Generate a unique id for this instance to be persisted across runs
        ts_key = self._generate_instance_key(instance)

        # Get all slowlog entries

        slowlogs = conn.slowlog_get(max_slow_entries)

        # Find slowlog entries between last timestamp and now using start_time
        slowlogs = [s for s in slowlogs if s['start_time'] > self.last_timestamp_seen[ts_key]]

        max_ts = 0
        # Slowlog entry looks like:
        #  {'command': 'LPOP somekey',
        #   'duration': 11238,
        #   'id': 496L,
        #   'start_time': 1422529869}
        for slowlog in slowlogs:
            if slowlog['start_time'] > max_ts:
                max_ts = slowlog['start_time']

            slowlog_tags = list(tags)
            command = slowlog['command'].split()
            # When the "Garantia Data" custom Redis is used, redis-py returns
            # an empty `command` field
            # FIXME when https://github.com/andymccurdy/redis-py/pull/622 is released in redis-py
            if command:
                slowlog_tags.append('command:{0}'.format(command[0]))

            value = slowlog['duration']
            self.histogram('redis.slowlog.micros', value, tags=slowlog_tags)

        self.last_timestamp_seen[ts_key] = max_ts

    def _check_command_stats(self, conn, tags):
        """Get command-specific statistics from redis' INFO COMMANDSTATS command
        """
        try:
            command_stats = conn.info("commandstats")
        except Exception:
            self.warning("Could not retrieve command stats from Redis."
                         "INFO COMMANDSTATS only works with Redis >= 2.6.")
            return

        for key, stats in command_stats.iteritems():
            command = key.split('_', 1)[1]
            command_tags = tags + ['command:%s' % command]
            self.gauge('redis.command.calls', stats['calls'], tags=command_tags)
            self.gauge('redis.command.usec_per_call', stats['usec_per_call'], tags=command_tags)

    def check(self, instance):
        if ("host" not in instance or "port" not in instance) and "unix_socket_path" not in instance:
            raise Exception("You must specify a host/port couple or a unix_socket_path")
        custom_tags = instance.get('tags', [])

        self._check_db(instance, custom_tags)
        self._check_slowlog(instance, custom_tags)

    def _collect_metadata(self, info):
        if info and 'redis_version' in info:
            self.service_metadata('version', info['redis_version'])
