# stdlib
import logging
import pprint
import random
import time

# 3p
from distutils.version import StrictVersion # pylint: disable=E0611,E0401
from nose.plugins.attrib import attr
from nose.plugins.skip import SkipTest
import redis

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest, load_check

logger = logging.getLogger()

MAX_WAIT = 20
NOAUTH_PORT = 16379
AUTH_PORT = 26379
SLAVE_HEALTHY_PORT = 36379
SLAVE_UNHEALTHY_PORT = 46379
DEFAULT_PORT = 6379
MISSING_KEY_TOLERANCE = 0.6


@attr(requires='redis')
class TestRedis(AgentCheckTest):
    CHECK_NAME = "redisdb"

    def test_redis_default(self):
        port = NOAUTH_PORT

        instance = {
            'host': 'localhost',
            'port': port
        }

        db = redis.Redis(port=port, db=14)  # Datadog's test db
        db.flushdb()
        db.set("key1", "value")
        db.set("key2", "value")
        db.setex("expirekey", "expirevalue", 1000)

        r = load_check('redisdb', {}, {})
        r.check(instance)
        metrics = self._sort_metrics(r.get_metrics())
        assert metrics, "No metrics returned"

        # Assert we have values, timestamps and tags for each metric.
        for m in metrics:
            assert isinstance(m[1], int)    # timestamp
            assert isinstance(m[2], (int, float, long))  # value
            tags = m[3]["tags"]
            expected_tags = ["redis_host:localhost", "redis_port:%s" % port]
            for e in expected_tags:
                assert e in tags

        def assert_key_present(expected, present, tolerance):
            "Assert we have the rest of the keys (with some tolerance for missing keys)"
            e = set(expected)
            p = set(present)
            assert len(e - p) < tolerance * len(e), pprint.pformat((p, e - p))

        # gauges collected?
        remaining_keys = [m[0] for m in metrics]
        expected = r.GAUGE_KEYS.values()
        assert_key_present(expected, remaining_keys, MISSING_KEY_TOLERANCE)

        # Assert that the keys metrics are tagged by db. just check db0, since
        # it's the only one we can guarantee is there.
        db_metrics = self._sort_metrics(
            [m for m in metrics if m[0] in ['redis.keys', 'redis.expires'] and "redis_db:db14" in m[3]["tags"]])
        self.assertEquals(2, len(db_metrics))

        self.assertEquals('redis.expires', db_metrics[0][0])
        self.assertEquals(1, db_metrics[0][2])

        self.assertEquals('redis.keys', db_metrics[1][0])
        self.assertEquals(3, db_metrics[1][2])

        # Service checks
        service_checks = r.get_service_checks()
        service_checks_count = len(service_checks)
        self.assertTrue(isinstance(service_checks, list))
        self.assertTrue(service_checks_count > 0)
        self.assertEquals(
            len([sc for sc in service_checks if sc['check'] == "redis.can_connect"]), 1, service_checks)
        # Assert that all service checks have the proper tags: host and port
        self.assertEquals(
            len([sc for sc in service_checks if "redis_host:localhost" in sc['tags']]),
            service_checks_count,
            service_checks)
        self.assertEquals(
            len([sc for sc in service_checks if "redis_port:%s" % port in sc['tags']]),
            service_checks_count,
            service_checks)

        # Run one more check and ensure we get total command count
        # and other rates
        time.sleep(5)
        r.check(instance)
        metrics = self._sort_metrics(r.get_metrics())
        keys = [m[0] for m in metrics]
        assert 'redis.net.commands' in keys

        # Service metadata
        service_metadata = r.get_service_metadata()
        service_metadata_count = len(service_metadata)
        self.assertTrue(service_metadata_count > 0)
        for meta_dict in service_metadata:
            assert meta_dict

    def test_slowlog(self):
        port = NOAUTH_PORT
        test_key = "testkey"
        instance = {
            'host': 'localhost',
            'port': port
        }

        db = redis.Redis(port=port, db=14)  # Datadog's test db

        # Tweaking Redis's config to have the test run faster
        old_sl_thresh = db.config_get('slowlog-log-slower-than')['slowlog-log-slower-than']
        db.config_set('slowlog-log-slower-than', 0)

        db.flushdb()

        # Generate some slow commands
        for i in range(100):
            db.lpush(test_key, random.random())

        db.sort(test_key)

        self.assertTrue(db.slowlog_len() > 0)

        db.config_set('slowlog-log-slower-than', old_sl_thresh)

        self.run_check({"init_config": {}, "instances": [instance]})

        assert self.metrics, "No metrics returned"
        self.assertMetric("redis.slowlog.micros.max", tags=["command:SORT",
            "redis_host:localhost", "redis_port:{0}".format(port)])

    def test_custom_slowlog(self):
        port = NOAUTH_PORT
        test_key = "testkey"
        instance = {
            'host': 'localhost',
            'port': port,
            'slowlog-max-len': 1
        }

        db = redis.Redis(port=port, db=14)  # Datadog's test db

        # Tweaking Redis's config to have the test run faster
        old_sl_thresh = db.config_get('slowlog-log-slower-than')['slowlog-log-slower-than']
        db.config_set('slowlog-log-slower-than', 0)

        db.flushdb()

        # Generate some slow commands
        for i in range(100):
            db.lpush(test_key, random.random())

        db.sort(test_key)

        db.config_set('slowlog-log-slower-than', old_sl_thresh)

        self.assertTrue(db.slowlog_len() > 0)

        self.run_check({"init_config": {}, "instances": [instance]})

        assert self.metrics, "No metrics returned"

        # Let's check that we didn't put more than one slowlog entry in the
        # payload, as specified in the above agent configuration
        self.assertMetric("redis.slowlog.micros.count", tags=["command:SORT",
            "redis_host:localhost", "redis_port:{0}".format(port)], value=1.0)

    def test_redis_command_stats(self):
        port = NOAUTH_PORT

        instance = {
            'host': 'localhost',
            'port': port,
            'command_stats': True
        }

        db = redis.Redis(port=port, db=14)  # Datadog's test db

        r = load_check('redisdb', {}, {})
        r.check(instance)

        version = db.info().get('redis_version')
        if StrictVersion(version) < StrictVersion('2.6.0'):
            raise SkipTest("Command stats only works with Redis >= 2.6.0")

        metrics = self._sort_metrics(r.get_metrics())
        assert metrics, "No metrics returned"
        command_stat_metrics = ['redis.command.calls', 'redis.command.usec', 'redis.command.usec_per_call']
        command_metrics = [m for m in metrics if m[0] in command_stat_metrics]

        # Assert we have values, timestamps and tags for each metric.
        for m in command_metrics:
            assert isinstance(m[1], int)    # timestamp
            assert isinstance(m[2], (int, float, long))  # value
            tags = m[3]["tags"]
            expected_tags = ["redis_host:localhost", "redis_port:%s" % port]
            for e in expected_tags:
                assert e in tags

        # Check the command stats for INFO, since we know we've called it
        info_metrics = self._sort_metrics(
            [m for m in command_metrics if "command:info" in m[3]["tags"]])
        # There should be one value for each metric for the info command
        self.assertEquals(2, len(info_metrics))

        self.assertEquals('redis.command.calls', info_metrics[0][0])
        assert info_metrics[0][2] > 0, "Number of INFO calls should be >0"

        self.assertEquals('redis.command.usec_per_call', info_metrics[1][0])
        assert info_metrics[1][2] > 0, "Usec per INFO call should be >0"

    def _sort_metrics(self, metrics):
        def sort_by(m):
            return m[0], m[1], m[3]
        return sorted(metrics, key=sort_by)