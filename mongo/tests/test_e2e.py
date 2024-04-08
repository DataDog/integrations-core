# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from packaging import version

from datadog_checks.mongo import MongoDb

from .common import HOST, MONGODB_VERSION, PORT1, auth, shard, standalone, tls

BASE_METRICS = [
    'mongodb.connections.available',
    'mongodb.metrics.cursor.open.pinned',
    'mongodb.connections.totalcreated',
    'mongodb.uptime',
    'mongodb.mem.bits',
    'mongodb.mem.resident',
    'mongodb.metrics.cursor.open.total',
    'mongodb.stats.avgobjsize',
    'mongodb.stats.storagesize',
    'mongodb.mem.virtual',
    'mongodb.dbs',
    'mongodb.connections.current',
    'mongodb.network.bytesinps',
    'mongodb.asserts.msgps',
    'mongodb.opcounters.queryps',
    'mongodb.opcounters.getmoreps',
    'mongodb.asserts.rolloversps',
    'mongodb.opcounters.deleteps',
    'mongodb.asserts.regularps',
    'mongodb.opcounters.insertps',
    'mongodb.asserts.warningps',
    'mongodb.network.numrequestsps',
    'mongodb.opcounters.updateps',
    'mongodb.asserts.userps',
    'mongodb.opcounters.commandps',
    'mongodb.extra_info.page_faultsps',
    'mongodb.network.bytesoutps',
]

MONGOS_METRICS = BASE_METRICS + [
    'mongodb.stats.indexsize',
    'mongodb.stats.datasize',
    'mongodb.stats.indexes',
    'mongodb.stats.objects',
]

MONGOS_METRICS_PRE_VERSION_7 = [
    'mongodb.stats.filesize',
]

MONGOD_METRICS = BASE_METRICS + [
    'mongodb.oplatencies.reads.latencyps',
    'mongodb.oplatencies.writes.latencyps',
    'mongodb.oplatencies.commands.latencyps',
    'mongodb.oplatencies.reads.latency',
    'mongodb.oplatencies.writes.latency',
    'mongodb.oplatencies.commands.latency',
    'mongodb.metrics.queryexecutor.scannedps',
    'mongodb.metrics.queryexecutor.scannedobjectsps',
    'mongodb.fsynclocked',
]


@standalone
@pytest.mark.e2e
def test_e2e_mongo_standalone(dd_agent_check, instance_user):
    aggregator = dd_agent_check(instance_user, rate=True)
    for metric in MONGOD_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_service_check('mongodb.can_connect', status=MongoDb.OK)


@shard
@pytest.mark.e2e
def test_e2e_mongo_shard(dd_agent_check, instance_authdb):
    aggregator = dd_agent_check(instance_authdb, rate=True)

    for metric in MONGOS_METRICS:
        aggregator.assert_metric(metric)

    if version.parse(MONGODB_VERSION) < version.parse('7.0'):
        for metric in MONGOS_METRICS_PRE_VERSION_7:
            aggregator.assert_metric(metric)
    aggregator.assert_service_check('mongodb.can_connect', status=MongoDb.OK)


@auth
@pytest.mark.e2e
def test_e2e_mongo_auth(dd_agent_check, instance_authdb):
    aggregator = dd_agent_check(instance_authdb, rate=True)
    for metric in MONGOD_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_service_check('mongodb.can_connect', status=MongoDb.OK)


@tls
@pytest.mark.e2e
def test_e2e_mongo_tls(dd_agent_check):
    instance = {
        'hosts': [f'{HOST}:{PORT1}'],
        'database': 'test',
        'tls': True,
        'tls_allow_invalid_certificates': True,
        'tls_certificate_key_file': '/certs/client1.pem',
        'tls_ca_file': '/certs/ca.pem',
    }
    aggregator = dd_agent_check(instance, rate=True)
    for metric in MONGOD_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_service_check('mongodb.can_connect', status=MongoDb.OK)
