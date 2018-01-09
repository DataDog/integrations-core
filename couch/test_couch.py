# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from urlparse import urljoin
import csv
import time
import threading
import random
import string
import re

# 3rd party
import requests
import json
from nose.plugins.attrib import attr

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest


@attr(requires='couch')
@attr(couch_version='1.x')
class CouchTestCase(AgentCheckTest):

    CHECK_NAME = 'couch'

    # Publicly readable databases
    DB_NAMES = ['_replicator', '_users', 'kennel']

    GLOBAL_GAUGES = [
        'couchdb.couchdb.auth_cache_hits',
        'couchdb.couchdb.auth_cache_misses',
        'couchdb.httpd.requests',
        'couchdb.httpd_request_methods.GET',
        'couchdb.httpd_request_methods.PUT',
        'couchdb.couchdb.request_time',
        'couchdb.couchdb.open_os_files',
        'couchdb.couchdb.open_databases',
        'couchdb.httpd_status_codes.200',
        'couchdb.httpd_status_codes.201',
        'couchdb.httpd_status_codes.400',
        'couchdb.httpd_status_codes.401',
        'couchdb.httpd_status_codes.404',
    ]

    CHECK_GAUGES = [
        'couchdb.by_db.disk_size',
        'couchdb.by_db.doc_count',
    ]

    def __init__(self, *args, **kwargs):
        AgentCheckTest.__init__(self, *args, **kwargs)
        self.config = {"instances": [{"server": "http://localhost:5984"}]}

    def test_couch(self):
        self.run_check(self.config)

        # Metrics should have been emitted for any publicly readable databases.
        for db_name in self.DB_NAMES:
            tags = ['instance:http://localhost:5984', 'db:{0}'.format(db_name)]
            for gauge in self.CHECK_GAUGES:
                self.assertMetric(gauge, tags=tags, count=1)

        # Check global metrics
        for gauge in self.GLOBAL_GAUGES:
            tags = ['instance:http://localhost:5984']
            self.assertMetric(gauge, tags=tags, at_least=0)

        self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                status=AgentCheck.OK,
                                tags=['instance:http://localhost:5984'],
                                count=2) # One per DB + one to get the version

        self.coverage_report()

    def test_bad_config(self):
        self.assertRaises(
            Exception,
            lambda: self.run_check({"instances": [{"server": "http://localhost:5985"}]})
        )

        self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                status=AgentCheck.CRITICAL,
                                tags=['instance:http://localhost:5985'],
                                count=1)

    def test_couch_whitelist(self):
        DB_WHITELIST = ["_users"]
        self.config['instances'][0]['db_whitelist'] = DB_WHITELIST
        self.run_check(self.config)
        for db_name in self.DB_NAMES:
            tags = ['instance:http://localhost:5984', 'db:{0}'.format(db_name)]
            for gauge in self.CHECK_GAUGES:
                if db_name in DB_WHITELIST:
                    self.assertMetric(gauge, tags=tags, count=1)
                else:
                    self.assertMetric(gauge, tags=tags, count=0)

    def test_couch_blacklist(self):
        DB_BLACKLIST = ["_replicator"]
        self.config['instances'][0]['db_blacklist'] = DB_BLACKLIST
        self.run_check(self.config)
        for db_name in self.DB_NAMES:
            tags = ['instance:http://localhost:5984', 'db:{0}'.format(db_name)]
            for gauge in self.CHECK_GAUGES:
                if db_name in DB_BLACKLIST:
                    self.assertMetric(gauge, tags=tags, count=0)
                else:
                    self.assertMetric(gauge, tags=tags, count=1)

    def test_only_max_nodes_are_scanned(self):
        self.config['instances'][0]['max_dbs_per_check'] = 1
        self.run_check(self.config)
        for db_name in self.DB_NAMES[1:]:
            tags = ['instance:http://localhost:5984', 'db:{0}'.format(db_name)]
            for gauge in self.CHECK_GAUGES:
                self.assertMetric(gauge, tags=tags, count=0)

@attr(requires='couch')
@attr(couch_version='2.x')
class TestCouchdb2(AgentCheckTest):
    """Basic Test for couchdb2 integration."""
    CHECK_NAME = 'couch'

    NODE1 = {
        'server': 'http://127.0.0.1:5984',
        'user': 'dduser',
        'password': 'pawprint',
        'name': 'node1@127.0.0.1'
    }

    NODE2 = {
        'server': 'http://127.0.0.1:5984',
        'user': 'dduser',
        'password': 'pawprint',
        'name': 'node2@127.0.0.1'
    }

    NODE3 = {
        'server': 'http://127.0.0.1:5984',
        'user': 'dduser',
        'password': 'pawprint',
        'name': 'node3@127.0.0.1'
    }

    def __init__(self, *args, **kwargs):
        AgentCheckTest.__init__(self, *args, **kwargs)
        self.cluster_gauges = []
        self.by_db_gauges = []
        self.erlang_gauges = []
        self.replication_tasks_gauges = []
        self.compaction_tasks_gauges = []
        self.indexing_tasks_gauges = []
        self.view_compaction_tasks_gauges = []
        self.by_dd_gauges = []
        with open('couch/metadata.csv', 'rb') as csvfile:
            reader = csv.reader(csvfile)
            reader.next() # This one skips the headers
            for row in reader:
                if row[0] in ['couchdb.couchdb.request_time', 'couchdb.by_db.disk_size']:
                    # Skip CouchDB 1.x specific metrics
                    continue
                elif row[0].startswith("couchdb.by_db."):
                    self.by_db_gauges.append(row[0])
                elif row[0].startswith("couchdb.erlang"):
                    self.erlang_gauges.append(row[0])
                elif row[0] in ['couchdb.active_tasks.replication.count', 'couchdb.active_tasks.db_compaction.count', 'couchdb.active_tasks.indexer.count', 'couchdb.active_tasks.view_compaction.count']:
                    self.cluster_gauges.append(row[0])
                elif row[0].startswith("couchdb.active_tasks.replication"):
                    self.replication_tasks_gauges.append(row[0])
                elif row[0].startswith("couchdb.active_tasks.db_compaction"):
                    self.compaction_tasks_gauges.append(row[0])
                elif row[0].startswith("couchdb.active_tasks.indexer"):
                    self.indexing_tasks_gauges.append(row[0])
                elif row[0].startswith("couchdb.active_tasks.view_compaction"):
                    self.view_compaction_tasks_gauges.append(row[0])
                elif row[0].startswith("couchdb.by_ddoc."):
                    self.by_dd_gauges.append(row[0])
                else:
                    self.cluster_gauges.append(row[0])

    def test_check(self):
        """
        Testing Couchdb2 check.
        """
        self.run_check({"instances": [self.NODE1, self.NODE2, self.NODE3]})

        tags = map(lambda n: "instance:{0}".format(n['name']), [self.NODE1, self.NODE2, self.NODE3])
        for tag in tags:
            for gauge in self.cluster_gauges:
                self.assertMetric(gauge, tags=[tag])

            for db in ['_users', '_global_changes', '_metadata', '_replicator', 'kennel']:
                for gauge in self.by_db_gauges:
                    self.assertMetric(gauge, tags=[tag, "db:{0}".format(db)])

            for gauge in self.erlang_gauges:
                self.assertMetric(gauge)

            for db, dd in {"kennel": "dummy", "_replicator": "_replicator", "_users": "_auth"}.items():
                for gauge in self.by_dd_gauges:
                    self.assertMetric(gauge, tags=[tag, "design_document:{0}".format(dd), "language:javascript", "db:{0}".format(db)])

        self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                status=AgentCheck.OK,
                                tags=["instance:{0}".format(self.NODE1["name"])],
                                count=2) # One for the version, one for the server stats

        for node in [self.NODE2, self.NODE3]:
            self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                    status=AgentCheck.OK,
                                    tags=["instance:{0}".format(node["name"])],
                                    count=1) # One for the server stats, the version is already loaded

        #  Raises when COVERAGE=true and coverage < 100%
        self.coverage_report()

    def test_bad_config(self):
        conf = self.NODE1.copy()
        conf.pop('server')
        self.assertRaises(
            Exception,
            lambda: self.run_check({"instances": [conf]})
        )

    def test_wrong_config(self):
        conf = self.NODE1.copy()
        conf['server'] = "http://127.0.0.1:11111"

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

        for n in [self.NODE1, self.NODE2, self.NODE3]:
            node = n.copy()
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

    def test_db_blacklisting(self):
        confs = []

        for n in [self.NODE1, self.NODE2, self.NODE3]:
            node = n.copy()
            node['db_blacklist'] = ['kennel']
            confs.append(node)

        self.run_check({"instances": confs})

        for n in confs:
            for db in ['_users', '_global_changes', '_metadata', '_replicator']:
                tags = ["instance:{0}".format(n['name']), "db:{0}".format(db)]
                for gauge in self.by_db_gauges:
                    self.assertMetric(gauge, tags=tags)

            tags = ["instance:{0}".format(n['name']), 'db:kennel']
            for gauge in self.by_db_gauges:
                self.assertMetric(gauge, tags=tags, count=0)

    def test_check_without_names(self):
        conf = self.NODE1.copy()
        conf.pop('name')

        self.run_check({"instances": [conf]})

        tags = map(lambda n: "instance:{0}".format(n['name']), [self.NODE1, self.NODE2, self.NODE3])
        for tag in tags:
            for gauge in self.cluster_gauges:
                self.assertMetric(gauge, tags=[tag])

            for db in ['_users', '_global_changes', '_metadata', '_replicator', 'kennel']:
                tags = [tag, "db:{0}".format(db)]
                for gauge in self.by_db_gauges:
                    self.assertMetric(gauge, tags=tags)

            for gauge in self.erlang_gauges:
                self.assertMetric(gauge)

            for db, dd in {"kennel": "dummy", "_replicator": "_replicator", "_users": "_auth"}.items():
                for gauge in self.by_dd_gauges:
                    self.assertMetric(gauge, tags=[tag, "design_document:{0}".format(dd), "language:javascript", "db:{0}".format(db)])

        self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                status=AgentCheck.OK,
                                tags=["instance:{0}".format(conf["server"])],
                                count=1) # One for the version as we don't have any names to begin with

        for node in [self.NODE1, self.NODE2, self.NODE3]:
            self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                    status=AgentCheck.OK,
                                    tags=["instance:{0}".format(node["name"])],
                                    count=1) # One for the server stats, the version is already loaded

        #  Raises when COVERAGE=true and coverage < 100%
        self.coverage_report()

    def test_only_max_nodes_are_scanned(self):
        conf = self.NODE1.copy()
        conf.pop('name')
        conf['max_nodes_per_check'] = 2

        self.run_check({"instances": [conf]})

        for gauge in self.erlang_gauges:
            self.assertMetric(gauge)

        tags = map(lambda n: "instance:{0}".format(n['name']), [self.NODE1, self.NODE2])
        for tag in tags:
            for gauge in self.cluster_gauges:
                self.assertMetric(gauge, tags=[tag])

            for db in ['_users', '_global_changes', '_metadata', '_replicator', 'kennel']:
                tags = [tag, "db:{0}".format(db)]
                for gauge in self.by_db_gauges:
                    self.assertMetric(gauge, tags=tags)

            for db, dd in {"kennel": "dummy", "_replicator": "_replicator", "_users": "_auth"}.items():
                for gauge in self.by_dd_gauges:
                    self.assertMetric(gauge, tags=[tag, "design_document:{0}".format(dd), "language:javascript", "db:{0}".format(db)])

        self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                status=AgentCheck.OK,
                                tags=["instance:{0}".format(conf["server"])],
                                count=1) # One for the version as we don't have any names to begin with

        for node in [self.NODE1, self.NODE2]:
            self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                    status=AgentCheck.OK,
                                    tags=["instance:{0}".format(node["name"])],
                                    count=1) # One for the server stats, the version is already loaded

        tags = ["instance:{0}".format(self.NODE3['name'])]
        for gauge in self.cluster_gauges:
            self.assertMetric(gauge, tags=tags, count=0)

        for db in ['_users', '_global_changes', '_metadata', '_replicator', 'kennel']:
            tags = [tags[0], "db:{0}".format(db)]
            for gauge in self.by_db_gauges:
                self.assertMetric(gauge, tags=tags, count=0)

        self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                status=AgentCheck.OK,
                                tags=tags,
                                count=0)

        #  Raises when COVERAGE=true and coverage < 100%
        self.coverage_report()

    def test_only_max_dbs_are_scanned(self):
        confs = []

        for n in [self.NODE1, self.NODE2, self.NODE3]:
            node = n.copy()
            node['max_dbs_per_check'] = 1
            confs.append(node)

        self.run_check({"instances": confs})

        for n in confs:
            for db in ['kennel', '_users', '_metadata', '_replicator']:
                tags = ["instance:{0}".format(n['name']), "db:{0}".format(db)]
                for gauge in self.by_db_gauges:
                    self.assertMetric(gauge, tags=tags, count=0)

            tags = ["instance:{0}".format(n['name']), 'db:_global_changes']
            for gauge in self.by_db_gauges:
                self.assertMetric(gauge, tags=tags, count=1)

    def test_replication_metrics(self):
        url = self.NODE1['server'] + '/_replicator'
        replication_body = {
            '_id': 'my_replication_id',
            'source': 'http://dduser:pawprint@127.0.0.1:5984/kennel',
            'target': 'http://dduser:pawprint@127.0.0.1:5984/kennel_replica',
            'create_target': True,
            'continuous': True
        }
        r = requests.post(url, auth=(self.NODE1['user'], self.NODE1['password']), headers={'Content-Type': 'application/json'}, data=json.dumps(replication_body))
        r.raise_for_status()

        count = 0
        attempts = 0
        while count != 1 and attempts < 20:
            attempts += 1
            time.sleep(1)
            r = requests.get(self.NODE1['server'] + '/_active_tasks', auth=(self.NODE1['user'], self.NODE1['password']))
            r.raise_for_status()
            count = len(r.json())

        self.run_check({"instances": [self.NODE1, self.NODE2, self.NODE3]})

        for gauge in self.replication_tasks_gauges:
            self.assertMetric(gauge)

    def test_compaction_metrics(self):
        url = urljoin(self.NODE1['server'], 'kennel')
        body = {
            '_id': 'fsdr2345fgwert249i9fg9drgsf4SDFGWE',
            'data': str(time.time())
        }
        r = requests.post(url, auth=(self.NODE1['user'], self.NODE1['password']), headers={'Content-Type': 'application/json'}, data=json.dumps(body))
        r.raise_for_status()

        update_url = urljoin(self.NODE1['server'], 'kennel/{0}'.format(body['_id']))

        for _ in xrange(50):
            rev = r.json()['rev']
            body['data'] = str(time.time())
            body['_rev'] = rev
            r = requests.put(update_url, auth=(self.NODE1['user'], self.NODE1['password']), headers={'Content-Type': 'application/json'}, data=json.dumps(body))
            r.raise_for_status()

            r2 = requests.post(url, auth=(self.NODE1['user'], self.NODE1['password']), headers={'Content-Type': 'application/json'}, data=json.dumps({"_id": str(time.time())}))
            r2.raise_for_status()

        url = urljoin(self.NODE1['server'], 'kennel/_compact')
        r = requests.post(url, auth=(self.NODE1['user'], self.NODE1['password']), headers={'Content-Type': 'application/json'})
        r.raise_for_status()

        url = urljoin(self.NODE1['server'], '_global_changes/_compact')
        r = requests.post(url, auth=(self.NODE1['user'], self.NODE1['password']), headers={'Content-Type': 'application/json'})
        r.raise_for_status()

        self.run_check({"instances": [self.NODE1, self.NODE2, self.NODE3]})

        for gauge in self.compaction_tasks_gauges:
            self.assertMetric(gauge)

    def test_indexing_metrics(self):
        url = urljoin(self.NODE1['server'], 'kennel')
        for _ in xrange(50):
            r = requests.post(url, auth=(self.NODE1['user'], self.NODE1['password']), headers={'Content-Type': 'application/json'}, data=json.dumps({"_id": str(time.time())}))
            r.raise_for_status()

        class AsyncReq(threading.Thread):
            def __init__(self, url, auth):
                self._url = url
                self._auth = auth
                threading.Thread.__init__(self)

            def run(self):
                r = requests.get(self._url, auth=self._auth)
                r.raise_for_status()

        url = urljoin(self.NODE1['server'], 'kennel/_design/dummy/_view/all')
        t = AsyncReq(url, (self.NODE1['user'], self.NODE1['password']))
        t.start()

        self.run_check({"instances": [self.NODE1, self.NODE2, self.NODE3]})

        t.join()

        for node in [self.NODE1, self.NODE2, self.NODE3]:
            for gauge in self.indexing_tasks_gauges:
                self.assertMetric(gauge, tags=['database:kennel', 'design_document:dummy', 'instance:{0}'.format(node['name'])])

    def test_view_compaction_metrics(self):
        class LoadGenerator(threading.Thread):
            STOP = 0
            RUN = 1

            def __init__(self, server, auth):
                self._server = server
                self._auth = auth
                self._status = self.RUN
                threading.Thread.__init__(self)

            def run(self):
                docs = []
                count = 0
                while self._status == self.RUN:
                    count += 1
                    if count % 5 == 0:
                        self.compact_views()
                    theid = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
                    docs.append(self.post_doc(theid))
                    docs = map(lambda x: self.update_doc(x), docs)
                    self.generate_views()

            def generate_views(self):
                url = urljoin(self._server, 'kennel/_design/dummy/_view/all')
                try:
                    r = requests.get(url, auth=self._auth, timeout=1)
                    r.raise_for_status()
                except requests.exceptions.Timeout:
                    None
                url = urljoin(self._server, 'kennel/_design/dummy/_view/by_data')
                try:
                    r = requests.get(url, auth=self._auth, timeout=1)
                    r.raise_for_status()
                except requests.exceptions.Timeout:
                    None

            def update_doc(self, doc):
                body = {
                    'data': str(random.randint(0, 1000000000)),
                    '_rev': doc['rev']
                }

                r = requests.put(urljoin(self._server, 'kennel/{0}'.format(doc['id'])), auth=self._auth, headers={'Content-Type': 'application/json'}, data=json.dumps(body))
                r.raise_for_status()
                return r.json()

            def post_doc(self, doc_id):
                body = {
                    "_id": doc_id,
                    "data": str(time.time())
                }
                r = requests.post(urljoin(self._server, 'kennel'), auth=self._auth, headers={'Content-Type': 'application/json'}, data=json.dumps(body))
                r.raise_for_status()
                return r.json()

            def compact_views(self):
                url = urljoin(self._server, 'kennel/_compact/dummy')
                r = requests.post(url, auth=self._auth, headers={'Content-Type': 'application/json'})
                r.raise_for_status()

            def stop(self):
                self._status = self.STOP

        threads = []
        for _ in range(40):
            t = LoadGenerator(self.NODE1['server'], (self.NODE1['user'], self.NODE1['password']))
            t.start()
            threads.append(t)

        tries = 0
        try:
            metric_found = False
            while not metric_found and tries < 20:
                tries += 1
                self.run_check({"instances": [self.NODE1, self.NODE2, self.NODE3]})

                for m_name, ts, val, mdata in self.metrics:
                    if re.search('view_compaction\.progress', m_name) is not None:
                        metric_found = True
                        for gauge in self.view_compaction_tasks_gauges:
                            self.assertMetric(gauge)
                        break
        finally:
            for t in threads:
                t.stop()

            for t in threads:
                t.join()

        if tries >= 20:
            self.fail("Could not find the view_compaction happening")
