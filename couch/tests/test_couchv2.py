# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import csv
import random
import re
import string
import threading
import time
from collections import defaultdict
from copy import deepcopy

import pytest
import requests
from six import PY2

from datadog_checks.couch import CouchDb

from . import common

pytestmark = pytest.mark.skipif(common.COUCH_MAJOR_VERSION != 2, reason='Test for version Couch v2')

INSTANCES = [common.NODE1, common.NODE2, common.NODE3]


@pytest.fixture(scope="module")
def gauges():
    res = defaultdict(list)
    if PY2:
        mode = "rb"
    else:
        mode = "r"

    with open("{}/../metadata.csv".format(common.HERE), mode) as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row[0] == 'metric_name':
                # skip the header
                continue
            elif row[0] in ["couchdb.couchdb.request_time", "couchdb.by_db.disk_size"]:
                # Skip CouchDB 1.x specific metrics
                continue
            elif row[0].startswith("couchdb.by_db."):
                res["by_db_gauges"].append(row[0])
            elif row[0].startswith("couchdb.erlang"):
                res["erlang_gauges"].append(row[0])
            elif row[0] in [
                "couchdb.active_tasks.replication.count",
                "couchdb.active_tasks.db_compaction.count",
                "couchdb.active_tasks.indexer.count",
                "couchdb.active_tasks.view_compaction.count",
            ]:
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


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_check(aggregator, gauges):
    for config in deepcopy(INSTANCES):
        check = CouchDb(common.CHECK_NAME, {}, [config])
        check.check(config)
    _assert_check(aggregator, gauges)


@pytest.mark.e2e
def test_e2e(dd_agent_check, gauges):
    aggregator = dd_agent_check({'init_config': {}, 'instances': deepcopy(INSTANCES)})
    _assert_check(aggregator, gauges)


def _assert_check(aggregator, gauges):
    """
    Testing Couchdb2 check.
    """
    for config in INSTANCES:
        expected_tags = ["instance:{}".format(config["name"])]
        for gauge in gauges["cluster_gauges"]:
            aggregator.assert_metric(gauge, tags=expected_tags)

        for gauge in gauges["erlang_gauges"]:
            aggregator.assert_metric(gauge)

    for db, dd in {"kennel": "dummy"}.items():
        for gauge in gauges["by_dd_gauges"]:
            expected_tags = ["design_document:{}".format(dd), "language:javascript", "db:{}".format(db)]
            aggregator.assert_metric(gauge, tags=expected_tags)

    for db in ["kennel", "db1"]:
        for gauge in gauges["by_db_gauges"]:
            expected_tags = ["db:{}".format(db)]
            aggregator.assert_metric(gauge, tags=expected_tags)

    expected_tags = ["instance:{}".format(common.NODE1["name"])]
    # One for the version, one for the server stats
    aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, status=CouchDb.OK, tags=expected_tags, count=2)

    for node in [common.NODE2, common.NODE3]:
        expected_tags = ["instance:{}".format(node["name"])]
        # One for the server stats, the version is already loaded
        aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, status=CouchDb.OK, tags=expected_tags, count=2)

    # Assert replication task metrics
    for gauge in gauges["replication_tasks_gauges"]:
        aggregator.assert_metric(gauge)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_db_whitelisting(aggregator, gauges):
    configs = []

    for n in [common.NODE1, common.NODE2, common.NODE3]:
        node = deepcopy(n)
        node['db_whitelist'] = ['db0', 'db2', 'db4']
        configs.append(node)

    for config in configs:
        check = CouchDb(common.CHECK_NAME, {}, [config])
        check.check(config)

    for _ in configs:
        for db in ['db0', 'db2', 'db4']:
            expected_tags = ["db:{}".format(db)]
            for gauge in gauges["by_db_gauges"]:
                aggregator.assert_metric(gauge, tags=expected_tags)

        for db in ['db1', 'db3']:
            expected_tags = ["db:{}".format(db)]
            for gauge in gauges["by_db_gauges"]:
                aggregator.assert_metric(gauge, tags=expected_tags, count=0)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_db_blacklisting(aggregator, gauges):
    configs = []

    for node in [common.NODE1, common.NODE2, common.NODE3]:
        config = deepcopy(node)
        config['db_blacklist'] = ['db0', 'db2', 'db4']
        configs.append(config)

    for config in configs:
        check = CouchDb(common.CHECK_NAME, {}, [config])
        check.check(config)

    for _ in configs:
        for db in ['db1', 'db3']:
            expected_tags = ["db:{}".format(db)]
            for gauge in gauges["by_db_gauges"]:
                aggregator.assert_metric(gauge, tags=expected_tags)

        for db in ['db0', 'db2', 'db4']:
            expected_tags = ["db:{}".format(db)]
            for gauge in gauges["by_db_gauges"]:
                aggregator.assert_metric(gauge, tags=expected_tags, count=0)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_check_without_names(aggregator, gauges):
    config = deepcopy(common.NODE1)
    config.pop('name')
    check = CouchDb(common.CHECK_NAME, {}, [config])
    check.check(config)

    configs = [common.NODE1, common.NODE2, common.NODE3]

    for config in configs:
        expected_tags = ["instance:{}".format(config["name"])]
        for gauge in gauges["cluster_gauges"]:
            aggregator.assert_metric(gauge, tags=expected_tags)

        for gauge in gauges["erlang_gauges"]:
            aggregator.assert_metric(gauge)

        for gauge in gauges["replication_tasks_gauges"]:
            aggregator.assert_metric(gauge)

    for db, dd in {"kennel": "dummy"}.items():
        expected_tags = ["design_document:{}".format(dd), "language:javascript", "db:{}".format(db)]
        for gauge in gauges["by_dd_gauges"]:
            aggregator.assert_metric(gauge, tags=expected_tags)

    for db in ["kennel"]:
        expected_tags = ["db:{}".format(db)]
        for gauge in gauges["by_db_gauges"]:
            aggregator.assert_metric(gauge, tags=expected_tags)

    expected_tags = ["instance:{}".format(config["server"])]
    # One for the version, one for the server stats
    aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, status=CouchDb.OK, tags=expected_tags, count=1)

    for node in [common.NODE2, common.NODE3]:
        expected_tags = ["instance:{}".format(node["name"])]
        # One for the server stats, the version is already loaded
        aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, status=CouchDb.OK, tags=expected_tags, count=1)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
@pytest.mark.parametrize('number_nodes', [1, 2, 3])
def test_only_max_nodes_are_scanned(aggregator, gauges, number_nodes):
    config = deepcopy(common.NODE1)
    config.pop("name")
    config['max_nodes_per_check'] = number_nodes

    check = CouchDb(common.CHECK_NAME, {}, [config])
    check.check(config)

    metrics = []
    for metric_list in aggregator._metrics.values():
        for m in metric_list:
            metrics.append(m)

    instance_tags = set()
    for m in metrics:
        for tag in m.tags:
            if tag.startswith('instance:'):
                instance_tags.add(tag)

    assert len(instance_tags) == number_nodes


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
@pytest.mark.parametrize('number_db', [1, 2, 3])
def test_only_max_dbs_are_scanned(aggregator, gauges, number_db):
    config = deepcopy(common.NODE1)
    config["max_dbs_per_check"] = number_db

    check = CouchDb(common.CHECK_NAME, {}, [config])
    check.check(config)

    metrics = []
    for metric_list in aggregator._metrics.values():
        for m in metric_list:
            metrics.append(m)

    db_tags = set()
    for m in metrics:
        for tag in m.tags:
            if tag.startswith('db:'):
                db_tags.add(tag)

    assert len(db_tags) == number_db


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_replication_metrics(aggregator, gauges):
    for config in [common.NODE1, common.NODE2, common.NODE3]:
        check = CouchDb(common.CHECK_NAME, {}, [config])
        check.check(config)

    for gauge in gauges["replication_tasks_gauges"]:
        aggregator.assert_metric(gauge)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_compaction_metrics(aggregator, gauges, active_tasks):
    """
    Database compaction tasks are super quick to run on small amounts of data, leading to the task sometimes
    being complete before the check queries for active tasks. This can lead to flaky results, so let's mock.
    """
    from datadog_checks.couch import couch

    def _get_active_tasks(server, name, tags):
        return active_tasks

    check = CouchDb(common.CHECK_NAME, {}, [common.NODE1])
    check.checker = couch.CouchDB2(check)
    check.checker._get_active_tasks = _get_active_tasks
    check.check(common.NODE1)

    for gauge in gauges["compaction_tasks_gauges"]:
        aggregator.assert_metric(gauge)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_indexing_metrics(aggregator, gauges, active_tasks):
    """
    Testing metrics coming from a running indexer would be extremely flaky,
    let's use mock.
    """
    from datadog_checks.couch import couch

    def _get(url, tags, run_check=False):
        if '_active_tasks' in url:
            return active_tasks
        return {}

    # run the check on all instances
    for config in [common.NODE1, common.NODE2, common.NODE3]:
        check = CouchDb(common.CHECK_NAME, {}, [config])
        check.checker = couch.CouchDB2(check)
        check.get = _get
        check.check(config)

    for node in [common.NODE1, common.NODE2, common.NODE3]:
        expected_tags = ['database:kennel', 'design_document:dummy', 'instance:{}'.format(node['name'])]
        for gauge in gauges["indexing_tasks_gauges"]:
            aggregator.assert_metric(gauge, tags=expected_tags)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_view_compaction_metrics(aggregator, gauges):
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
                docs = list(map(lambda x: self.update_doc(x), docs))
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
            body = {'data': str(random.randint(0, 1000000000)), '_rev': doc['rev']}

            url = '{}/kennel/{}'.format(self._server, doc['id'])
            r = requests.put(url, auth=self._auth, headers={'Content-Type': 'application/json'}, json=body)
            r.raise_for_status()
            return r.json()

        def post_doc(self, doc_id):
            body = {"_id": doc_id, "data": str(time.time())}
            url = '{}/kennel'.format(self._server)
            r = requests.post(url, auth=self._auth, headers={'Content-Type': 'application/json'}, json=body)
            r.raise_for_status()
            return r.json()

        def compact_views(self):
            url = '{}/kennel/_compact/dummy'.format(self._server)
            r = requests.post(url, auth=self._auth, headers={'Content-Type': 'application/json'})
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

            try:
                for config in [common.NODE1, common.NODE2, common.NODE3]:
                    check = CouchDb(common.CHECK_NAME, {}, [config])
                    check.check(config)
            except Exception:
                time.sleep(1)
                continue

            for m_name in aggregator._metrics:
                if re.search(r'view_compaction\.progress', str(m_name)) is not None:
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
        raise AssertionError('Could not find the view_compaction happening')


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_config_tags(aggregator, gauges):
    TEST_TAG = "test_tag:test"
    config = deepcopy(common.NODE1)
    config['tags'] = [TEST_TAG]

    check = CouchDb(common.CHECK_NAME, {}, [config])
    check.check(config)

    for gauge in gauges["erlang_gauges"]:
        aggregator.assert_metric_has_tag(gauge, TEST_TAG)
    for gauge in gauges["by_db_gauges"]:
        aggregator.assert_metric_has_tag(gauge, TEST_TAG)
    expected_tags = ["instance:{0}".format(config["name"]), TEST_TAG]
    aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, tags=expected_tags)
