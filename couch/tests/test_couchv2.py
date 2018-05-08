# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy
from collections import defaultdict
import csv
import random
import re
import string
import time
import threading

import pytest
import requests

from datadog_checks.couch import CouchDb
import common

pytestmark = pytest.mark.v2


@pytest.fixture(scope="module")
def gauges():
    res = defaultdict(list)
    with open("{}/../metadata.csv".format(common.HERE), "rb") as csvfile:
        reader = csv.reader(csvfile)
        reader.next()  # This one skips the headers
        for row in reader:
            if row[0] in ["couchdb.couchdb.request_time", "couchdb.by_db.disk_size"]:
                # Skip CouchDB 1.x specific metrics
                continue
            elif row[0].startswith("couchdb.by_db."):
                res["by_db_gauges"].append(row[0])
            elif row[0].startswith("couchdb.erlang"):
                res["erlang_gauges"].append(row[0])
            elif row[0] in ["couchdb.active_tasks.replication.count", "couchdb.active_tasks.db_compaction.count",
                            "couchdb.active_tasks.indexer.count", "couchdb.active_tasks.view_compaction.count"]:
                res["cluster_gauges"].append(row[0])
            elif row[0].startswith("couchdb.active_tasks.replication"):
                res["replication_tasks_gauges"].append(row[0])
            elif row[0].startswith("couchdb.active_tasks.db_compaction"):
                res["compaction_tasks_gauges"].append(row[0])
            elif row[0].startswith("couchdb.active_tasks.indexer"):
                res["indexing_tasks_gauges"].append(row[0])
            elif row[0].startswith("couchdb.active_tasks.view_compaction"):
                res["view_compaction_tasks_gauges"].append(row[0])
            elif row[0].startswith("couchdb.by_ddoc."):
                res["by_dd_gauges"].append(row[0])
            else:
                res["cluster_gauges"].append(row[0])
        yield res


def test_check(aggregator, check, gauges, couch_cluster):
    """
    Testing Couchdb2 check.
    """
    configs = [deepcopy(common.NODE1), deepcopy(common.NODE2), deepcopy(common.NODE3)]

    for config in configs:
        check.check(config)

    for config in configs:
        expected_tags = ["instance:{}".format(config["name"])]
        for gauge in gauges["cluster_gauges"]:
            aggregator.assert_metric(gauge, tags=expected_tags)

        for gauge in gauges["erlang_gauges"]:
            aggregator.assert_metric(gauge)

    for db, dd in {"kennel": "dummy", "_replicator": "_replicator", "_users": "_auth"}.items():
        for gauge in gauges["by_dd_gauges"]:
            expected_tags = [
                "design_document:{}".format(dd),
                "language:javascript",
                "db:{}".format(db)
            ]
            aggregator.assert_metric(gauge, tags=expected_tags)

    for db in ["_users", "_global_changes", "_metadata", "_replicator", "kennel"]:
        for gauge in gauges["by_db_gauges"]:
            expected_tags = ["db:{}".format(db)]
            aggregator.assert_metric(gauge, tags=expected_tags)

    expected_tags = ["instance:{}".format(common.NODE1["name"])]
    # One for the version, one for the server stats
    aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, status=CouchDb.OK, tags=expected_tags, count=2)

    for node in [common.NODE2, common.NODE3]:
        expected_tags = ["instance:{}".format(node["name"])]
        # One for the server stats, the version is already loaded
        aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, status=CouchDb.OK, tags=expected_tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_db_whitelisting(aggregator, check, gauges, couch_cluster):
    configs = []

    for n in [common.NODE1, common.NODE2, common.NODE3]:
        node = deepcopy(n)
        node['db_whitelist'] = ['kennel']
        configs.append(node)

    for config in configs:
        check.check(config)

    for _ in configs:
        for db in ['_users', '_global_changes', '_metadata', '_replicator']:
            expected_tags = ["db:{}".format(db)]
            for gauge in gauges["by_db_gauges"]:
                aggregator.assert_metric(gauge, tags=expected_tags, count=0)

        for gauge in gauges["by_db_gauges"]:
            expected_tags = ["db:kennel"]
            aggregator.assert_metric(gauge, tags=expected_tags)


def test_db_blacklisting(aggregator, check, gauges, couch_cluster):
    configs = []

    for node in [common.NODE1, common.NODE2, common.NODE3]:
        config = deepcopy(node)
        config['db_blacklist'] = ['kennel']
        configs.append(config)

    for config in configs:
        check.check(config)

    for _ in configs:
        for db in ['_users', '_global_changes', '_metadata', '_replicator']:
            expected_tags = ["db:{}".format(db)]
            for gauge in gauges["by_db_gauges"]:
                aggregator.assert_metric(gauge, tags=expected_tags)

        for gauge in gauges["by_db_gauges"]:
            expected_tags = ["db:kennel"]
            aggregator.assert_metric(gauge, tags=expected_tags, count=0)


def test_check_without_names(aggregator, check, gauges, couch_cluster):
    config = deepcopy(common.NODE1)
    config.pop('name')
    check.check(config)

    configs = [common.NODE1, common.NODE2, common.NODE3]

    for config in configs:
        expected_tags = ["instance:{}".format(config["name"])]
        for gauge in gauges["cluster_gauges"]:
            aggregator.assert_metric(gauge, tags=expected_tags)

        for gauge in gauges["erlang_gauges"]:
            aggregator.assert_metric(gauge)

    for db, dd in {"kennel": "dummy", "_replicator": "_replicator", "_users": "_auth"}.items():
        expected_tags = [
            "design_document:{}".format(dd),
            "language:javascript",
            "db:{}".format(db)
        ]
        for gauge in gauges["by_dd_gauges"]:
            aggregator.assert_metric(gauge, tags=expected_tags)

    for db in ["_users", "_global_changes", "_metadata", "_replicator", "kennel"]:
        expected_tags = ["db:{}".format(db)]
        for gauge in gauges["by_db_gauges"]:
            aggregator.assert_metric(gauge, tags=expected_tags)

    expected_tags = [
        "instance:{}".format(config["server"])
    ]
    # One for the version, one for the server stats
    aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, status=CouchDb.OK, tags=expected_tags, count=1)

    for node in [common.NODE2, common.NODE3]:
        expected_tags = ["instance:{}".format(node["name"])]
        # One for the server stats, the version is already loaded
        aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, status=CouchDb.OK, tags=expected_tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_only_max_nodes_are_scanned(aggregator, check, gauges, couch_cluster):
    config = deepcopy(common.NODE1)
    config.pop("name")
    config['max_nodes_per_check'] = 2

    check.check(config)

    for gauge in gauges["erlang_gauges"]:
        aggregator.assert_metric(gauge)

    for config in [common.NODE1, common.NODE2]:
        expected_tags = ["instance:{}".format(config["name"])]
        for gauge in gauges["cluster_gauges"]:
            aggregator.assert_metric(gauge, tags=expected_tags)

    for db in ["_users", "_global_changes", "_metadata", "_replicator"]:
        expected_tags = ["db:{}".format(db)]
        for gauge in gauges["by_db_gauges"]:
            aggregator.assert_metric(gauge, tags=expected_tags)

    for db, dd in {"_replicator": "_replicator", "_users": "_auth"}.items():
        expected_tags = [
            "design_document:{}".format(dd),
            "language:javascript",
            "db:{}".format(db)
        ]
        for gauge in gauges["by_dd_gauges"]:
            aggregator.assert_metric(gauge, tags=expected_tags)

    expected_tags = ["instance:{}".format(config["server"])]
    # One for the version as we don't have any names to begin with
    aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, status=CouchDb.OK, tags=expected_tags, count=1)

    for node in [common.NODE1, common.NODE2]:
        expected_tags = ["instance:{}".format(node["name"])]
        # One for the server stats, the version is already loaded
        aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, status=CouchDb.OK, tags=expected_tags, count=1)

    expected_tags = ["instance:{}".format(common.NODE3["name"])]
    for gauge in gauges["cluster_gauges"]:
        aggregator.assert_metric(gauge, tags=expected_tags, count=0)

    for db in ['_users', '_global_changes', '_metadata', '_replicator', 'kennel']:
        expected_tags = [expected_tags[0], "db:{}".format(db)]
        for gauge in gauges["by_db_gauges"]:
            aggregator.assert_metric(gauge, tags=expected_tags, count=0)

    expected_tags = ["instance:{}".format(common.NODE3["name"])]
    aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, status=CouchDb.OK, tags=expected_tags, count=0)

    aggregator.assert_all_metrics_covered()


def test_only_max_dbs_are_scanned(aggregator, check, gauges, couch_cluster):
    configs = []
    for node in [common.NODE1, common.NODE2, common.NODE3]:
        config = deepcopy(node)
        config["max_dbs_per_check"] = 1
        configs.append(config)

    for config in configs:
        check.check(config)

    for db in ['_users', '_metadata']:
        expected_tags = ["instance:{}".format(node["name"])]
        for gauge in gauges["by_db_gauges"]:
            aggregator.assert_metric(gauge, tags=expected_tags, count=0)

    for db in ['_global_changes', 'kennel', '_replicator']:
        expected_tags = ["db:{}".format(db)]
        for gauge in gauges["by_db_gauges"]:
            aggregator.assert_metric(gauge, tags=expected_tags, count=1)


def test_replication_metrics(aggregator, check, gauges, couch_cluster):
    url = "{}/_replicator".format(common.NODE1['server'])
    replication_body = {
        '_id': 'my_replication_id',
        'source': 'http://dduser:pawprint@127.0.0.1:5984/kennel',
        'target': 'http://dduser:pawprint@127.0.0.1:5984/kennel_replica',
        'create_target': True,
        'continuous': True
    }
    r = requests.post(
        url,
        auth=(common.NODE1['user'], common.NODE1['password']),
        headers={'Content-Type': 'application/json'},
        json=replication_body
    )
    r.raise_for_status()

    count = 0
    attempts = 0
    url = "{}/_active_tasks".format(common.NODE1['server'])
    while count != 1 and attempts < 20:
        attempts += 1
        time.sleep(1)
        r = requests.get(url, auth=(common.NODE1['user'], common.NODE1['password']))
        r.raise_for_status()
        count = len(r.json())

    check = CouchDb(common.CHECK_NAME, {}, {})
    for config in [common.NODE1, common.NODE2, common.NODE3]:
        check.check(config)

    for gauge in gauges["replication_tasks_gauges"]:
        aggregator.assert_metric(gauge)


def test_compaction_metrics(aggregator, check, gauges, couch_cluster):
    url = "{}/kennel".format(common.NODE1['server'])
    body = {
        '_id': 'fsdr2345fgwert249i9fg9drgsf4SDFGWE',
        'data': str(time.time())
    }
    r = requests.post(
        url,
        auth=(common.NODE1['user'], common.NODE1['password']),
        headers={'Content-Type': 'application/json'},
        json=body
    )
    r.raise_for_status()

    update_url = '{}/{}'.format(url, body['_id'])

    for _ in xrange(50):
        rev = r.json()['rev']
        body['data'] = str(time.time())
        body['_rev'] = rev
        r = requests.put(
            update_url,
            auth=(common.NODE1['user'], common.NODE1['password']),
            headers={'Content-Type': 'application/json'},
            json=body
        )
        r.raise_for_status()

        r2 = requests.post(
            url,
            auth=(common.NODE1['user'], common.NODE1['password']),
            headers={'Content-Type': 'application/json'},
            json={"_id": str(time.time())}
        )
        r2.raise_for_status()

    url = '{}/kennel/_compact'.format(common.NODE1['server'])
    r = requests.post(
        url,
        auth=(common.NODE1['user'], common.NODE1['password']),
        headers={'Content-Type': 'application/json'}
    )
    r.raise_for_status()

    url = '{}/_global_changes/_compact'.format(common.NODE1['server'])
    r = requests.post(
        url,
        auth=(common.NODE1['user'], common.NODE1['password']),
        headers={'Content-Type': 'application/json'}
    )
    r.raise_for_status()

    for config in [common.NODE1, common.NODE2, common.NODE3]:
        check.check(config)

    for gauge in gauges["compaction_tasks_gauges"]:
        aggregator.assert_metric(gauge)


def test_indexing_metrics(aggregator, check, gauges, active_tasks):
    """
    Testing metrics coming from a running indexer would be extremely flaky,
    let's use mock.
    """
    from datadog_checks.couch import couch
    check.checker = couch.CouchDB2(check)

    def _get(url, instance, tags, run_check=False):
        if '_active_tasks' in url:
            return active_tasks
        return {}
    check.get = _get

    # run the check on all instances
    for config in [common.NODE1, common.NODE2, common.NODE3]:
        check.check(config)

    for node in [common.NODE1, common.NODE2, common.NODE3]:
        expected_tags = [
            'database:kennel',
            'design_document:dummy',
            'instance:{}'.format(node['name'])
        ]
        for gauge in gauges["indexing_tasks_gauges"]:
            aggregator.assert_metric(gauge, tags=expected_tags)


def test_view_compaction_metrics(aggregator, check, gauges, couch_cluster):
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
            url = '{}/kennel/_design/dummy/_view/all'.format(self._server)
            try:
                r = requests.get(url, auth=self._auth, timeout=1)
                r.raise_for_status()
            except requests.exceptions.Timeout:
                None
            url = '{}/kennel/_design/dummy/_view/by_data'.format(self._server)
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

            url = '{}/kennel/{}'.format(self._server, doc['id'])
            r = requests.put(
                url,
                auth=self._auth,
                headers={'Content-Type': 'application/json'},
                json=body
            )
            r.raise_for_status()
            return r.json()

        def post_doc(self, doc_id):
            body = {
                "_id": doc_id,
                "data": str(time.time())
            }
            url = '{}/kennel'.format(self._server)
            r = requests.post(
                url,
                auth=self._auth,
                headers={'Content-Type': 'application/json'},
                json=body
            )
            r.raise_for_status()
            return r.json()

        def compact_views(self):
            url = '{}/kennel/_compact/dummy'.format(self._server)
            r = requests.post(
                url,
                auth=self._auth,
                headers={'Content-Type': 'application/json'}
            )
            r.raise_for_status()

        def stop(self):
            self._status = self.STOP

    threads = []
    for _ in range(40):
        t = LoadGenerator(common.NODE1['server'], (common.NODE1['user'], common.NODE1['password']))
        t.start()
        threads.append(t)

    tries = 0
    try:
        metric_found = False
        while not metric_found and tries < 40:
            tries += 1
            for config in [common.NODE1, common.NODE2, common.NODE3]:
                check.check(config)

            for m_name in aggregator._metrics:
                if re.search('view_compaction\.progress', m_name) is not None:
                    metric_found = True
                    for gauge in gauges["view_compaction_tasks_gauges"]:
                        aggregator.assert_metric(gauge)
                    break
    finally:
        for t in threads:
            t.stop()

        for t in threads:
            t.join()

    if tries >= 20:
        assert False, "Could not find the view_compaction happening"


def test_config_tags(aggregator, check, gauges, couch_cluster):
    TEST_TAG = "test_tag:test"
    config = deepcopy(common.NODE1)
    config['tags'] = [TEST_TAG]

    check.check(config)

    for gauge in gauges["erlang_gauges"]:
        aggregator.assert_metric_has_tag(gauge, TEST_TAG)
    for gauge in gauges["by_db_gauges"]:
        aggregator.assert_metric_has_tag(gauge, TEST_TAG)
    expected_tags = [
        "instance:{0}".format(config["name"]),
        TEST_TAG
    ]
    aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, tags=expected_tags)
