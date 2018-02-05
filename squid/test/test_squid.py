# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from nose.plugins.attrib import attr

# 3p

# project
from tests.checks.common import AgentCheckTest

expected_metrics = [
    "client_http.requests",
    "client_http.hits",
    "client_http.errors",
    "client_http.kbytes_in",
    "client_http.kbytes_out",
    "client_http.hit_kbytes_out",
    "server.all.requests",
    "server.all.errors",
    "server.all.kbytes_in",
    "server.all.kbytes_out",
    "server.http.requests",
    "server.http.errors",
    "server.http.kbytes_in",
    "server.http.kbytes_out",
    "server.ftp.requests",
    "server.ftp.errors",
    "server.ftp.kbytes_in",
    "server.ftp.kbytes_out",
    "server.other.requests",
    "server.other.errors",
    "server.other.kbytes_in",
    "server.other.kbytes_out",
    "icp.pkts_sent",
    "icp.pkts_recv",
    "icp.queries_sent",
    "icp.replies_sent",
    "icp.queries_recv",
    "icp.replies_recv",
    "icp.query_timeouts",
    "icp.replies_queued",
    "icp.kbytes_sent",
    "icp.kbytes_recv",
    "icp.q_kbytes_sent",
    "icp.r_kbytes_sent",
    "icp.q_kbytes_recv",
    "icp.r_kbytes_recv",
    "icp.times_used",
    "cd.times_used",
    "cd.msgs_sent",
    "cd.msgs_recv",
    "cd.memory",
    "cd.local_memory",
    "cd.kbytes_sent",
    "cd.kbytes_recv",
    "unlink.requests",
    "page_faults",
    "select_loops",
    "cpu_time",
    "swap.outs",
    "swap.ins",
    "swap.files_cleaned",
    "aborted_requests",
]

@attr(requires="squid")
class TestSquidIntegration(AgentCheckTest):
    """Integration tests for squid."""
    CHECK_NAME = "squid"

    def test_check_ok(self):
        conf = {
            "init_config": {},
            "instances": [{
                "name": "ok_instance",
                "tags": ["custom_tag"]
            }]
        }
        self.run_check_twice(conf)
        self.assertServiceCheckOK("squid.can_connect", tags=["name:ok_instance", "custom_tag"])
        for metric in expected_metrics:
            self.assertMetric("squid.cachemgr." + metric, tags=["name:ok_instance", "custom_tag"])
        self.coverage_report()

    def test_check_fail(self):
        conf = {
            "init_config": {},
            "instances": [{
                "name": "fail_instance",
                "host": "bad_host"
            }]
        }
        self.assertRaises(Exception, self.run_check_twice, conf)
        self.assertServiceCheckCritical("squid.can_connect", tags=["name:fail_instance"])

class TestSquidUnit(AgentCheckTest):
    """Unit tests for squid"""
    CHECK_NAME = "squid"

    def test_parse_counter(self):
        self.load_check({}, {})

        # Good format
        line = "counter = 0\n"
        counter, value = self.check.parse_counter(line)
        self.assertEquals(counter, "counter")
        self.assertEquals(value, "0")

        # Bad format
        line = "counter: value\n"
        counter, value = self.check.parse_counter(line)
        self.assertEquals(counter, None)
        self.assertEquals(value, None)

    def test_parse_instance(self):
        self.load_check({}, {})

        # instance with defaults
        instance = {
            "name": "ok_instance"
        }
        name, host, port, cachemgr_user, cachemgr_passwd, custom_tags = self.check.parse_instance(instance)
        self.assertEquals(name, "ok_instance")
        self.assertEquals(host, "localhost")
        self.assertEquals(port, 3128)
        self.assertEquals(cachemgr_passwd, "")
        self.assertEquals(cachemgr_user, "")
        self.assertEquals(custom_tags, [])

        # instance no defaults
        instance = {
            "name": "ok_instance",
            "host": "host",
            "port": 1234,
            "cachemgr_username": "datadog",
            "cachemgr_password": "pass",
            "tags": ["foo:bar"],
        }
        name, host, port, cachemgr_user, cachemgr_passwd, custom_tags = self.check.parse_instance(instance)
        self.assertEquals(name, "ok_instance")
        self.assertEquals(host, "host")
        self.assertEquals(port, 1234)
        self.assertEquals(cachemgr_user, "datadog")
        self.assertEquals(cachemgr_passwd, "pass")
        self.assertEquals(custom_tags, ["foo:bar"])

        # instance no name
        instance = {
            "host": "host"
        }
        self.assertRaises(Exception, self.check.parse_instance)
