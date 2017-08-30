# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from nose.plugins.attrib import attr
import csv

# 3p

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest

node1 = {
    'host': 'http://127.0.0.1',
    'cport': '15984',
    'backdoor': '15986',
    'user': 'dduser',
    'password': 'pawprint'
}

node2 = {
    'host': 'http://127.0.0.1',
    'cport': '25984',
    'backdoor': '25986',
    'user': 'dduser',
    'password': 'pawprint'
}

node3 = {
    'host': 'http://127.0.0.1',
    'cport': '35984',
    'backdoor': '35986',
    'user': 'dduser',
    'password': 'pawprint'
}

# NOTE: Feel free to declare multiple test classes if needed

@attr(requires='couchdb2')
class TestCouchdb2(AgentCheckTest):
    """Basic Test for couchdb2 integration."""
    CHECK_NAME = 'couchdb2'

    def __init__(self, *args, **kwargs):
        AgentCheckTest.__init__(self, *args, **kwargs)
        self.cluster_gauges = []
        self.by_db_gauges = []
        with open('couchdb2/metadata.csv', 'rb') as csvfile:
            reader = csv.reader(csvfile)
            reader.next()
            for row in reader:
                if row[0].startswith("couchdb.by_db."):
                    self.by_db_gauges.append(row[0])
                else:
                    self.cluster_gauges.append(row[0])

    def test_check(self):
        """
        Testing Couchdb2 check.
        """
        self.run_check({"instances": [node1, node2, node3]})

        tags = ['instance:http://127.0.0.1']
        for gauge in self.cluster_gauges:
            self.assertMetric(gauge, tags=tags)

        for db in ['_users', '_global_changes', '_metadata', '_replicator', 'kennel']:
            tags = ['instance:http://127.0.0.1', "db:{0}".format(db)]
            for gauge in self.by_db_gauges:
                self.assertMetric(gauge, tags=tags)

        for node in [node1, node2, node3]:
            self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                    status=AgentCheck.OK,
                                    tags=["instance:{0}:{1}".format(node['host'], node['backdoor'])],
                                    count=1)

        # Raises when COVERAGE=true and coverage < 100%
        self.coverage_report()

    def test_bad_config(self):
        conf = node1.copy()
        conf.pop('host')
        self.assertRaises(
                Exception,
                lambda: self.run_check({"instances": [conf]})
                )

    def test_wrong_config(self):
        conf = node1.copy()
        conf['backdoor'] = 11111

        self.assertRaises(
                Exception,
                lambda: self.run_check({"instances": [conf]})
                )

        self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                status=AgentCheck.CRITICAL,
                tags=["instance:{0}:{1}".format(conf['host'], conf['backdoor'])],
                count=1)

    def test_db_whitelisting(self):
        confs = []

        for n in [node1, node2, node3]:
            node = node1.copy()
            node['db_whitelist'] = ['kennel']
            confs.append(node)

        self.run_check({"instances": confs})

        for db in ['_users', '_global_changes', '_metadata', '_replicator']:
            tags = ['instance:http://127.0.0.1', "db:{0}".format(db)]
            for gauge in self.by_db_gauges:
                self.assertMetric(gauge, tags=tags, count=0)

        tags = ['instance:http://127.0.0.1', 'db:kennel']
        for gauge in self.by_db_gauges:
            self.assertMetric(gauge, tags=tags)
