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
    'host': 'http://127.0.0.1:5984',
    'user': 'dduser',
    'password': 'pawprint',
    'name': 'node1@127.0.0.1'
}

node2 = {
    'host': 'http://127.0.0.1:5984',
    'user': 'dduser',
    'password': 'pawprint',
    'name': 'node2@127.0.0.1'
}

node3 = {
    'host': 'http://127.0.0.1:5984',
    'user': 'dduser',
    'password': 'pawprint',
    'name': 'node3@127.0.0.1'
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

        tags = map(lambda n: ["instance:{0}".format(n['name'])], [node1, node2, node3])
        for tag in tags:
            for gauge in self.cluster_gauges:
                self.assertMetric(gauge, tags=tag)

            for db in ['_users', '_global_changes', '_metadata', '_replicator', 'kennel']:
                tags = [tag[0], "db:{0}".format(db)]
                for gauge in self.by_db_gauges:
                    self.assertMetric(gauge, tags=tags)

        for node in [node1, node2, node3]:
            self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                    status=AgentCheck.OK,
                                    tags=["instance:{0}".format(node["name"])],
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
        conf['host'] = "http://127.0.0.1:11111"

        self.assertRaises(
            Exception,
            lambda: self.run_check({"instances": [conf]})
        )

        self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                status=AgentCheck.CRITICAL,
                                tags=["instance:{0}".format(conf['name'])],
                                count=1)

    def test_db_whitelisting(self):
        confs = []

        for n in [node1, node2, node3]:
            node = node1.copy()
            node['db_whitelist'] = ['kennel']
            confs.append(node)

        self.run_check({"instances": confs})

        for n in confs:
            for db in ['_users', '_global_changes', '_metadata', '_replicator']:
                tags = ["instance:{0}".format(n['name']), "db:{0}".format(db)]
                for gauge in self.by_db_gauges:
                    self.assertMetric(gauge, tags=tags, count=0)

            tags = ["instance:{0}".format(n['name']), 'db:kennel']
            for gauge in self.by_db_gauges:
                self.assertMetric(gauge, tags=tags)
